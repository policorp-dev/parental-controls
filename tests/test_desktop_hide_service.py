"""Tests for desktop_hide_service and per-app desktop isolation."""

import json
import subprocess
import unittest
from unittest.mock import MagicMock, patch

from big_parental_controls.services import desktop_hide_service


class TestDesktopHideService(unittest.TestCase):
    """Test desktop hiding operations."""

    @patch("big_parental_controls.services.desktop_hide_service.subprocess.run")
    def test_get_hidden_desktop_ids(self, mock_run: MagicMock) -> None:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps(["facebook.desktop", "instagram.desktop"]),
        )
        hidden = desktop_hide_service.get_hidden_desktop_ids("testuser")
        self.assertEqual(hidden, {"facebook.desktop", "instagram.desktop"})
        mock_run.assert_called_once_with(
            ["pkexec", desktop_hide_service.GROUP_HELPER, "desktop-get-user-hidden", "testuser"],
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
        )

    @patch("big_parental_controls.services.desktop_hide_service.subprocess.run")
    def test_get_hidden_desktop_ids_failure(self, mock_run: MagicMock) -> None:
        mock_run.side_effect = OSError("failed")
        hidden = desktop_hide_service.get_hidden_desktop_ids("testuser")
        self.assertEqual(hidden, set())

    @patch("big_parental_controls.services.desktop_hide_service._refresh_menu_cache")
    @patch("big_parental_controls.services.desktop_hide_service.subprocess.run")
    def test_hide_desktop(self, mock_run: MagicMock, mock_refresh: MagicMock) -> None:
        result = desktop_hide_service.hide_desktop("testuser", "facebook.desktop")
        self.assertTrue(result)
        mock_run.assert_called_once_with(
            ["pkexec", desktop_hide_service.GROUP_HELPER, "desktop-hide", "testuser", "facebook.desktop"],
            check=True,
            timeout=30,
        )
        mock_refresh.assert_called_once_with("testuser")

    @patch("big_parental_controls.services.desktop_hide_service._refresh_menu_cache")
    @patch("big_parental_controls.services.desktop_hide_service.subprocess.run")
    def test_unhide_desktop(self, mock_run: MagicMock, mock_refresh: MagicMock) -> None:
        result = desktop_hide_service.unhide_desktop("testuser", "facebook.desktop")
        self.assertTrue(result)
        mock_run.assert_called_once_with(
            ["pkexec", desktop_hide_service.GROUP_HELPER, "desktop-unhide", "testuser", "facebook.desktop"],
            check=True,
            timeout=30,
        )
        mock_refresh.assert_called_once_with("testuser")

    @patch("big_parental_controls.services.desktop_hide_service._refresh_menu_cache")
    @patch("big_parental_controls.services.desktop_hide_service.subprocess.run")
    def test_batch_desktop_changes(self, mock_run: MagicMock, mock_refresh: MagicMock) -> None:
        result = desktop_hide_service.batch_desktop_changes(
            "testuser",
            ["facebook.desktop", "whatsapp.desktop"],
            ["twitter.desktop"],
        )
        self.assertTrue(result)
        mock_run.assert_called_once_with(
            [
                "pkexec",
                desktop_hide_service.GROUP_HELPER,
                "desktop-batch",
                "testuser",
                "facebook.desktop,whatsapp.desktop",
                "twitter.desktop",
            ],
            check=True,
            timeout=30,
        )
        mock_refresh.assert_called_once_with("testuser")

    @patch("big_parental_controls.services.desktop_hide_service.hide_desktop")
    def test_hide_app_with_desktop_id(self, mock_hide_desktop: MagicMock) -> None:
        mock_hide_desktop.return_value = True
        result = desktop_hide_service.hide_app("testuser", "facebook.desktop")
        self.assertTrue(result)
        mock_hide_desktop.assert_called_once_with("testuser", "facebook.desktop")

    @patch("big_parental_controls.services.desktop_hide_service.unhide_desktop")
    def test_unhide_app_with_desktop_id(self, mock_unhide_desktop: MagicMock) -> None:
        mock_unhide_desktop.return_value = True
        result = desktop_hide_service.unhide_app("testuser", "facebook.desktop")
        self.assertTrue(result)
        mock_unhide_desktop.assert_called_once_with("testuser", "facebook.desktop")


if __name__ == "__main__":
    unittest.main()
