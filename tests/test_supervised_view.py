"""Tests for SupervisedView."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from big_parental_controls.ui.pages.supervised_view import SupervisedView, _HELP_RESOURCES
from big_parental_controls.utils.i18n import setup_i18n

_ = setup_i18n()


class DummyActivityBlock(Gtk.Box):
    def load_user(self, username: str) -> None:
        pass


class TestSupervisedViewHelpSection(unittest.TestCase):
    """Test that help section links are activatable, show text and visual indicator, and fallback to copy with toast."""

    @patch("big_parental_controls.ui.pages.supervised_view.AccountsServiceWrapper")
    @patch("big_parental_controls.ui.pages.supervised_view.ActivityBlock", DummyActivityBlock)
    def test_help_expander_row_used(self, mock_accounts):
        mock_accounts_instance = MagicMock()
        mock_accounts_instance.get_current_user.return_value = None
        mock_accounts.return_value = mock_accounts_instance

        view = SupervisedView()

        def find_expander_rows(widget):
            rows = []
            if isinstance(widget, Adw.ExpanderRow):
                rows.append(widget)
            child = widget.get_first_child() if hasattr(widget, "get_first_child") else None
            while child:
                rows.extend(find_expander_rows(child))
                child = child.get_next_sibling()
            return rows

        expander_rows = find_expander_rows(view)
        self.assertEqual(len(expander_rows), 1)
        self.assertEqual(expander_rows[0].get_title(), _("Help and Support"))
        self.assertTrue(expander_rows[0].get_expanded())

    @patch("big_parental_controls.ui.pages.supervised_view.AccountsServiceWrapper")
    @patch("big_parental_controls.ui.pages.supervised_view.ActivityBlock", DummyActivityBlock)
    def test_help_resources_activatable_and_display_values_and_indicators(
        self, mock_accounts
    ):
        mock_accounts_instance = MagicMock()
        mock_accounts_instance.get_current_user.return_value = None
        mock_accounts.return_value = mock_accounts_instance

        view = SupervisedView()
        self.assertIsInstance(view, SupervisedView)

        def find_action_rows(widget):
            rows = []
            if isinstance(widget, Adw.ActionRow):
                rows.append(widget)
            child = widget.get_first_child() if hasattr(widget, "get_first_child") else None
            while child:
                rows.extend(find_action_rows(child))
                child = child.get_next_sibling()
            return rows

        action_rows = find_action_rows(view)
        self.assertGreater(len(action_rows), 0)
        for row in action_rows:
            self.assertTrue(row.get_activatable())

    @patch("big_parental_controls.ui.pages.supervised_view.AccountsServiceWrapper")
    @patch("big_parental_controls.ui.pages.supervised_view.ActivityBlock", DummyActivityBlock)
    @patch("big_parental_controls.ui.pages.supervised_view.Gio.AppInfo.get_default_for_uri_scheme")
    def test_indicator_icon_depends_on_app_handler(self, mock_get_default_app, mock_accounts):
        mock_accounts_instance = MagicMock()
        mock_accounts_instance.get_current_user.return_value = None
        mock_accounts.return_value = mock_accounts_instance

        mock_get_default_app.side_effect = lambda scheme: MagicMock() if scheme == "https" else None

        view = SupervisedView()

        def find_action_rows(widget):
            rows = []
            if isinstance(widget, Adw.ActionRow):
                rows.append(widget)
            child = widget.get_first_child() if hasattr(widget, "get_first_child") else None
            while child:
                rows.extend(find_action_rows(child))
                child = child.get_next_sibling()
            return rows

        action_rows = find_action_rows(view)
        # Verify that rows with https have external-link icon, tel without app have copy icon
        def find_images(widget):
            imgs = []
            if isinstance(widget, Gtk.Image):
                imgs.append(widget.get_icon_name())
            child = widget.get_first_child() if hasattr(widget, "get_first_child") else None
            while child:
                imgs.extend(find_images(child))
                child = child.get_next_sibling()
            return imgs

        icons = []
        for row in action_rows:
            icons.extend(find_images(row))

        self.assertIn("adw-external-link-symbolic", icons)
        self.assertIn("edit-copy-symbolic", icons)

    @patch("big_parental_controls.ui.pages.supervised_view.AccountsServiceWrapper")
    @patch("big_parental_controls.ui.pages.supervised_view.ActivityBlock", DummyActivityBlock)
    @patch("big_parental_controls.ui.pages.supervised_view.Adw.Toast.new")
    def test_copy_to_clipboard_shows_toast(self, mock_toast_new, mock_accounts):
        mock_accounts_instance = MagicMock()
        mock_accounts_instance.get_current_user.return_value = None
        mock_accounts.return_value = mock_accounts_instance

        mock_toast = MagicMock()
        mock_toast_new.return_value = mock_toast

        view = SupervisedView()
        with patch.object(view._toast_overlay, "add_toast") as mock_add_toast:
            view._copy_to_clipboard("test_value")
            mock_toast_new.assert_called_once()
            mock_add_toast.assert_called_once_with(mock_toast)

    @patch("big_parental_controls.ui.pages.supervised_view.AccountsServiceWrapper")
    @patch("big_parental_controls.ui.pages.supervised_view.ActivityBlock", DummyActivityBlock)
    @patch("big_parental_controls.ui.pages.supervised_view.Gio.AppInfo.get_default_for_uri_scheme")
    @patch("big_parental_controls.ui.pages.supervised_view.Gtk.UriLauncher")
    def test_link_activation_with_launcher(self, mock_launcher_cls, mock_get_default_app, mock_accounts):
        mock_accounts_instance = MagicMock()
        mock_accounts_instance.get_current_user.return_value = None
        mock_accounts.return_value = mock_accounts_instance

        mock_get_default_app.return_value = MagicMock()
        mock_launcher_instance = MagicMock()
        mock_launcher_cls.return_value = mock_launcher_instance

        view = SupervisedView()
        with patch.object(view, "_copy_to_clipboard") as mock_copy:
            view._on_help_row_activated(None, "https://example.com", "https://example.com")
            mock_launcher_cls.assert_called_once_with(uri="https://example.com")
            mock_launcher_instance.launch.assert_called_once()
            mock_copy.assert_not_called()

    @patch("big_parental_controls.ui.pages.supervised_view.AccountsServiceWrapper")
    @patch("big_parental_controls.ui.pages.supervised_view.ActivityBlock", DummyActivityBlock)
    @patch("big_parental_controls.ui.pages.supervised_view.Gio.AppInfo.get_default_for_uri_scheme")
    def test_link_activation_without_launcher_copies_text(self, mock_get_default_app, mock_accounts):
        mock_accounts_instance = MagicMock()
        mock_accounts_instance.get_current_user.return_value = None
        mock_accounts.return_value = mock_accounts_instance

        mock_get_default_app.return_value = None

        view = SupervisedView()
        with patch.object(view, "_copy_to_clipboard") as mock_copy:
            view._on_help_row_activated(None, "tel:188", "188")
            mock_copy.assert_called_once_with("188")

    @patch("big_parental_controls.ui.pages.supervised_view.AccountsServiceWrapper")
    @patch("big_parental_controls.ui.pages.supervised_view.ActivityBlock", DummyActivityBlock)
    @patch("big_parental_controls.ui.pages.supervised_view.Gio.AppInfo.get_default_for_uri_scheme")
    @patch("big_parental_controls.ui.pages.supervised_view.Gtk.UriLauncher")
    def test_link_activation_launcher_error_falls_back_to_copy(self, mock_launcher_cls, mock_get_default_app, mock_accounts):
        mock_accounts_instance = MagicMock()
        mock_accounts_instance.get_current_user.return_value = None
        mock_accounts.return_value = mock_accounts_instance

        mock_get_default_app.return_value = MagicMock()
        mock_launcher_instance = MagicMock()
        mock_launcher_cls.return_value = mock_launcher_instance

        def fake_launch(parent, cancellable, callback):
            fake_res = MagicMock()
            mock_launcher_instance.launch_finish.side_effect = RuntimeError("Launcher failed")
            callback(mock_launcher_instance, fake_res)

        mock_launcher_instance.launch.side_effect = fake_launch

        view = SupervisedView()
        with patch.object(view, "_copy_to_clipboard") as mock_copy:
            view._on_help_row_activated(None, "https://example.com", "https://example.com")
            mock_copy.assert_called_once_with("https://example.com")


if __name__ == "__main__":
    unittest.main()
