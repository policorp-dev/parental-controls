"""Main application window — AdwNavigationView based push/pop navigation."""

import os
import subprocess

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk

from big_parental_controls.services.accounts_service import AccountsServiceWrapper
from big_parental_controls.utils.async_runner import run_async
from big_parental_controls.utils.i18n import setup_i18n

_ = setup_i18n()

POLKIT_ACTION = "br.com.biglinux.parental-controls.manage-settings"


class MainWindow(Adw.ApplicationWindow):
    """Primary window with push/pop navigation."""

    __gtype_name__ = "MainWindow"

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.set_default_size(950, 680)
        self.set_title(_("Parental Controls"))
        self._accounts = AccountsServiceWrapper()
        self._is_supervised = self._accounts.is_current_user_supervised()
        self._admin_authenticated = False
        self._setup_navigation()

    def _setup_navigation(self) -> None:
        if self._is_supervised:
            self._setup_supervised_navigation()
            return

        # Admin user: show auth gate first
        self._show_auth_gate()

    def _show_auth_gate(self) -> None:
        """Show authentication screen before granting admin access."""
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        toolbar.add_top_bar(header)

        # Use Adw.StatusPage for a modern, central locked state
        status_page = Adw.StatusPage()
        status_page.set_icon_name("system-lock-screen-symbolic")
        status_page.set_title(_("Parental Controls"))
        status_page.set_description(
            _("Administrator authentication is required to change settings.")
        )

        # Action container for button and feedback
        action_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=16,
            halign=Gtk.Align.CENTER,
        )

        self._auth_spinner = Gtk.Spinner()
        self._auth_spinner.set_visible(False)
        action_box.append(self._auth_spinner)

        self._auth_status = Gtk.Label()
        self._auth_status.add_css_class("dim-label")
        self._auth_status.set_visible(False)
        action_box.append(self._auth_status)

        auth_btn = Gtk.Button(label=_("Authenticate"))
        auth_btn.add_css_class("suggested-action")
        auth_btn.add_css_class("pill")
        auth_btn.set_size_request(180, -1)
        auth_btn.connect("clicked", self._on_auth_clicked)
        action_box.append(auth_btn)

        status_page.set_child(action_box)
        toolbar.set_content(status_page)
        self.set_content(toolbar)

    def _on_auth_clicked(self, _btn: Gtk.Button) -> None:
        """Trigger polkit authentication via pkexec."""
        self._auth_spinner.set_visible(True)
        self._auth_spinner.start()
        self._auth_status.set_visible(False)

        def authenticate() -> bool:
            pid = os.getpid()
            try:
                subprocess.run(
                    [
                        "pkcheck",
                        "--action-id", POLKIT_ACTION,
                        "--process", str(pid),
                        "--allow-user-interaction",
                    ],
                    check=True,
                    timeout=120,
                )
                return True
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                return False

        def on_done(success: bool) -> None:
            self._auth_spinner.stop()
            self._auth_spinner.set_visible(False)
            if success:
                self._admin_authenticated = True
                self._setup_admin_navigation()
            else:
                self._auth_status.set_label(
                    _("Authentication failed. Try again.")
                )
                self._auth_status.set_visible(True)

        run_async(authenticate, on_done)

    def _setup_supervised_navigation(self) -> None:
        """Supervised user: read-only view with own usage data only."""
        from big_parental_controls.ui.pages.supervised_view import (
            SupervisedView,
        )

        view = SupervisedView()
        self.set_content(view)

    def _setup_admin_navigation(self) -> None:
        """Admin/parent user: full navigation with all controls."""
        from big_parental_controls.ui.pages.main_view import MainView

        self._nav_view = Adw.NavigationView()
        self._nav_view.set_vexpand(True)
        self._main_view = MainView(window=self)

        main_page = Adw.NavigationPage()
        main_page.set_title(_("Parental Controls"))
        main_page.set_child(self._main_view)
        main_page.set_tag("main")
        self._nav_view.add(main_page)

        self._toast_banner = Adw.Banner()
        self._toast_banner.set_revealed(False)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.append(self._toast_banner)
        box.append(self._nav_view)
        self.set_content(box)

    def show_user_detail(self, user: object) -> None:
        """Push the user detail page onto the navigation stack."""
        if self._is_supervised:
            return
        from big_parental_controls.ui.pages.user_detail_page import (
            UserDetailPage,
        )

        detail = UserDetailPage(user=user, window=self)
        page = Adw.NavigationPage()
        uname = user.get_real_name() or user.get_user_name()
        page.set_title(f"{_('Parental Controls')} — {uname}")
        page.set_child(detail)
        page.set_tag(f"user-{user.get_user_name()}")
        self._nav_view.push(page)

    def show_time_limits(self, user: object) -> None:
        """Push time limits editor for a specific user."""
        if self._is_supervised:
            return
        from big_parental_controls.ui.pages.time_limits_page import (
            TimeLimitsPage,
        )

        page_widget = TimeLimitsPage(user=user)
        nav_page = Adw.NavigationPage()
        nav_page.set_title(_("Screen Time"))
        nav_page.set_child(page_widget)
        self._nav_view.push(nav_page)

    def show_app_filter(self, user: object) -> None:
        """Push app filter editor for a specific user."""
        if self._is_supervised:
            return
        from big_parental_controls.ui.pages.app_filter_page import (
            AppFilterPage,
        )

        page_widget = AppFilterPage(user=user)
        nav_page = Adw.NavigationPage()
        nav_page.set_title(_("App Access"))
        nav_page.set_child(page_widget)
        self._nav_view.push(nav_page)

    def show_dns_settings(self, user: object) -> None:
        """Push DNS filter editor for a specific user."""
        if self._is_supervised:
            return
        from big_parental_controls.ui.pages.dns_page import DnsPage

        page_widget = DnsPage(user=user)
        nav_page = Adw.NavigationPage()
        nav_page.set_title(_("Web Filter"))
        nav_page.set_child(page_widget)
        self._nav_view.push(nav_page)

    def show_add_user(self) -> None:
        """Push the users management page."""
        if self._is_supervised:
            return
        from big_parental_controls.ui.pages.users_page import UsersPage

        page_widget = UsersPage()
        nav_page = Adw.NavigationPage()
        nav_page.set_title(_("Users"))
        nav_page.set_child(page_widget)
        self._nav_view.push(nav_page)

    def refresh_main_and_pop(self) -> None:
        """Refresh main view users list and pop back to it."""
        if self._is_supervised:
            return
        self._main_view.refresh_users()
        self._nav_view.pop_to_tag("main")

    def show_toast(self, message: str) -> None:
        """Show a styled success dialog that the user dismisses with OK."""
        dialog = Adw.AlertDialog()

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_margin_top(8)
        box.set_margin_bottom(4)
        box.set_margin_start(8)
        box.set_margin_end(8)

        icon = Gtk.Image(icon_name="emblem-ok-symbolic", pixel_size=64)
        icon.add_css_class("success")
        icon.set_halign(Gtk.Align.CENTER)
        box.append(icon)

        lbl = Gtk.Label(label=message)
        lbl.set_wrap(True)
        lbl.set_max_width_chars(32)
        lbl.set_justify(Gtk.Justification.CENTER)
        lbl.add_css_class("title-2")
        lbl.set_halign(Gtk.Align.CENTER)
        box.append(lbl)

        dialog.set_extra_child(box)
        dialog.add_response("ok", _("OK"))
        dialog.set_default_response("ok")
        dialog.present(self)

    def _dismiss_toast_banner(self) -> bool:
        self._toast_banner.set_revealed(False)
        return GLib.SOURCE_REMOVE

    def show_error(self, message: str) -> None:
        """Show an error dialog."""
        dialog = Adw.AlertDialog()
        dialog.set_heading(_("Error"))
        dialog.set_body(message)
        dialog.add_response("ok", _("OK"))
        dialog.set_default_response("ok")
        dialog.present(self)
