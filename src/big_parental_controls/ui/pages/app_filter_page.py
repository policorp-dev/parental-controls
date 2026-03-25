"""App filter page — manage per-user app access."""

import json
import shutil
import subprocess

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk

from big_parental_controls.core.constants import GROUP_HELPER
from big_parental_controls.services.accounts_service import AccountsServiceWrapper
from big_parental_controls.services.malcontent_service import MalcontentService
from big_parental_controls.services import desktop_hide_service
from big_parental_controls.utils.async_runner import run_async
from big_parental_controls.utils.i18n import setup_i18n

_ = setup_i18n()


class AppFilterPage(Gtk.Box):
    """Page for managing per-user app access control."""

    def __init__(self, user: object | None = None, **kwargs: object) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0, **kwargs)
        self._accounts = AccountsServiceWrapper()
        try:
            self._malcontent = MalcontentService()
        except GLib.Error:
            self._malcontent = None
        self._initial_user = user
        self._selected_uid: int | None = None
        self._selected_username: str | None = None
        self._pending_changes: dict[str, bool] = {}
        self._app_rows: dict[str, Adw.SwitchRow] = {}
        self._filter_text: str = ""
        self._build_ui()

    def _build_ui(self) -> None:
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        toolbar.add_top_bar(header)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        clamp = Adw.Clamp()
        clamp.set_maximum_size(600)

        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        inner.set_margin_top(24)
        inner.set_margin_bottom(24)
        inner.set_margin_start(24)
        inner.set_margin_end(24)

        # User selector
        selector_group = Adw.PreferencesGroup()
        self._user_combo = Adw.ComboRow()
        self._user_combo.set_title(_("User"))
        self._user_model = Gtk.StringList()
        self._user_combo.set_model(self._user_model)
        self._user_combo.connect("notify::selected", self._on_user_changed)
        selector_group.add(self._user_combo)
        inner.append(selector_group)

        # Empty state
        self._empty_status = Adw.StatusPage()
        self._empty_status.set_icon_name("application-x-executable-symbolic")
        self._empty_status.set_title(_("Select a User"))
        self._empty_status.set_description(_("Choose a supervised user to manage app access."))
        inner.append(self._empty_status)

        # Search entry
        self._search_entry = Gtk.SearchEntry()
        self._search_entry.set_placeholder_text(_("Filter apps…"))
        self._search_entry.set_visible(False)
        self._search_entry.connect("search-changed", self._on_search_changed)
        inner.append(self._search_entry)

        # Apps group
        self._apps_group = Adw.PreferencesGroup()
        self._apps_group.set_title(_("Installed Apps"))
        self._apps_group.set_visible(False)
        inner.append(self._apps_group)

        # Apply button
        self._apply_btn = Gtk.Button(label=_("Apply Changes"))
        self._apply_btn.add_css_class("suggested-action")
        self._apply_btn.set_sensitive(False)
        self._apply_btn.set_halign(Gtk.Align.END)
        self._apply_btn.connect("clicked", self._on_apply)
        inner.append(self._apply_btn)

        clamp.set_child(inner)
        scrolled.set_child(clamp)
        toolbar.set_content(scrolled)
        self.append(toolbar)

        self._populate_user_combo()

    def _populate_user_combo(self) -> None:
        """Populate user dropdown with supervised users."""
        self._supervised_users = []
        self._user_model.splice(0, self._user_model.get_n_items(), [])

        preselect_idx = 0
        for user in self._accounts.list_users():
            if self._accounts.is_supervised(user):
                if (
                    self._initial_user is not None
                    and user.get_uid() == self._initial_user.get_uid()
                ):
                    preselect_idx = len(self._supervised_users)
                self._supervised_users.append(user)
                label = user.get_real_name() or user.get_user_name()
                self._user_model.append(label)

        if self._supervised_users:
            self._user_combo.set_selected(preselect_idx)

    def _on_user_changed(self, combo: Adw.ComboRow, _pspec: object) -> None:
        idx = combo.get_selected()
        if idx == Gtk.INVALID_LIST_POSITION or idx >= len(self._supervised_users):
            return

        user = self._supervised_users[idx]
        self._selected_uid = user.get_uid()
        self._selected_username = user.get_user_name()
        self._empty_status.set_visible(False)
        self._apps_group.set_visible(True)
        self._search_entry.set_visible(True)
        self._pending_changes.clear()
        self._apply_btn.set_sensitive(False)
        self._filter_text = ""
        self._search_entry.set_text("")
        self._load_apps()

    def _load_apps(self) -> None:
        """Load installed apps and their blocked status."""
        # Clear rows
        while True:
            child = self._apps_group.get_first_child()
            if child is None:
                break
            if not isinstance(child, Adw.SwitchRow):
                child = child.get_next_sibling()
                if child is None:
                    break
                continue
            self._apps_group.remove(child)

        self._app_rows.clear()

        if self._selected_uid is None:
            return

        # Read ACL state via privileged helper so the root-owned JSON is
        # always accessible regardless of file permissions or user context.
        acl_blocked: set[str] = set()
        username = self._selected_username or ""
        if username:
            try:
                result = subprocess.run(
                    ["pkexec", GROUP_HELPER, "acl-get-user-blocks", username],
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=20,
                )
                if result.returncode == 0:
                    blocked_list = json.loads(result.stdout or "[]")
                    if isinstance(blocked_list, list):
                        acl_blocked = set(blocked_list)
            except (OSError, subprocess.TimeoutExpired, json.JSONDecodeError):
                pass

        shown_paths: set[str] = set()

        for app_info in Gio.AppInfo.get_all():
            if not app_info.should_show():
                continue
            exe = app_info.get_executable()
            if not exe:
                continue

            # Resolve to absolute path so acl-batch can find the file
            abs_exe = exe if exe.startswith("/") else (shutil.which(exe) or exe)

            name = app_info.get_display_name()
            app_id = app_info.get_id() or abs_exe

            # ACL state takes priority over malcontent OARS
            if abs_exe in acl_blocked:
                allowed = False
            elif self._malcontent:
                try:
                    allowed = self._malcontent.is_appinfo_allowed(self._selected_uid, app_info)
                except Exception:  # noqa: BLE001 — malcontent D-Bus is optional
                    allowed = True
            else:
                allowed = True

            row = Adw.SwitchRow()
            row.set_title(name)
            row.set_subtitle(abs_exe)
            row.set_active(allowed)
            row.connect("notify::active", self._on_app_toggled, app_id, abs_exe)

            icon = app_info.get_icon()
            if icon:
                img = Gtk.Image.new_from_gicon(icon)
                img.set_pixel_size(32)
                row.add_prefix(img)

            row.set_visible(self._row_matches_filter(name, abs_exe))
            self._apps_group.add(row)
            self._app_rows[app_id] = row
            shown_paths.add(abs_exe)

        # Show ACL-blocked apps that have no visible .desktop entry
        # (e.g. /usr/bin/rustdesk installed but NoDisplay=true system-wide)
        for blocked_path in sorted(acl_blocked - shown_paths):
            name = shutil.which(blocked_path) and blocked_path.split("/")[-1] or blocked_path
            app_id = blocked_path
            row = Adw.SwitchRow()
            row.set_title(name)
            row.set_subtitle(blocked_path)
            row.set_active(False)
            row.connect("notify::active", self._on_app_toggled, app_id, blocked_path)
            img = Gtk.Image.new_from_icon_name("application-x-executable-symbolic")
            img.set_pixel_size(32)
            row.add_prefix(img)
            row.set_visible(self._row_matches_filter(name, blocked_path))
            self._apps_group.add(row)
            self._app_rows[app_id] = row

    def _row_matches_filter(self, name: str, path: str) -> bool:
        if not self._filter_text:
            return True
        needle = self._filter_text.lower()
        return needle in name.lower() or needle in path.lower()

    def _on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        self._filter_text = entry.get_text().strip()
        for row in self._app_rows.values():
            title = row.get_title()
            subtitle = row.get_subtitle() or ""
            row.set_visible(self._row_matches_filter(title, subtitle))

    def _on_app_toggled(
        self, row: Adw.SwitchRow, _pspec: object, app_id: str, exe: str
    ) -> None:
        self._pending_changes[exe] = row.get_active()
        self._apply_btn.set_sensitive(True)

    def _on_apply(self, _button: Gtk.Button) -> None:
        """Apply pending changes via ACL batch."""
        if not self._selected_username or not self._pending_changes:
            return

        username = self._selected_username
        block_paths = [path for path, allowed in self._pending_changes.items() if not allowed]
        unblock_paths = [path for path, allowed in self._pending_changes.items() if allowed]

        def do_apply() -> None:
            import subprocess

            block_csv = ",".join(block_paths) if block_paths else ""
            unblock_csv = ",".join(unblock_paths) if unblock_paths else ""
            subprocess.run(
                ["pkexec", GROUP_HELPER, "acl-batch", username, block_csv, unblock_csv],
                check=True,
                timeout=60,
            )
            for path in block_paths:
                desktop_hide_service.hide_app(username, path)
            for path in unblock_paths:
                desktop_hide_service.unhide_app(username, path)

        def on_done(_result: object) -> None:
            self._pending_changes.clear()
            self._apply_btn.set_sensitive(False)
            self._show_success(_("App access updated."))

        def on_error(exc: Exception) -> None:
            self._show_error(str(exc))

        run_async(do_apply, on_done, on_error)

    def _show_success(self, message: str) -> None:
        window = self.get_root()
        if hasattr(window, "show_toast"):
            window.show_toast(message)

    def _show_error(self, message: str) -> None:
        window = self.get_root()
        if hasattr(window, "show_error"):
            window.show_error(message)

    def refresh(self) -> None:
        """Refresh user list and app list."""
        self._populate_user_combo()
