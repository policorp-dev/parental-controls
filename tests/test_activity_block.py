"""Tests for ActivityBlock UI component."""

from datetime import datetime
import unittest
from unittest.mock import MagicMock, patch

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk

from big_parental_controls.services.activity_service import SessionEntry
from big_parental_controls.ui.widgets.activity_block import ActivityBlock
from big_parental_controls.utils.i18n import setup_i18n

_ = setup_i18n()


class TestActivityBlockSessions(unittest.TestCase):
    """Test that ActivityBlock uses Adw.ExpanderRow for Sessions."""

    def test_sessions_expander_exists(self) -> None:
        block = ActivityBlock()
        self.assertIsInstance(block._sessions_expander, Adw.ExpanderRow)
        self.assertEqual(block._sessions_expander.get_title(), _("Sessions"))

    def test_populate_sessions_empty(self) -> None:
        block = ActivityBlock()
        block._populate_sessions([])
        self.assertEqual(len(block._session_rows), 1)
        self.assertEqual(block._sessions_expander.get_subtitle(), _("No sessions on this day"))
        self.assertEqual(block._session_rows[0].get_title(), _("No sessions on this day"))

    def test_populate_sessions_with_entries(self) -> None:
        block = ActivityBlock()
        sessions = [
            SessionEntry(
                start=datetime(2026, 10, 25, 9, 0),
                end=datetime(2026, 10, 25, 10, 30),
                duration_minutes=90,
                tty="seat0",
                session_type="wayland",
            ),
            SessionEntry(
                start=datetime(2026, 10, 25, 14, 0),
                end=None,
                duration_minutes=45,
                tty="seat0",
                session_type="wayland",
            ),
        ]
        block._populate_sessions(sessions)
        self.assertEqual(len(block._session_rows), 2)
        self.assertIn("2", block._sessions_expander.get_subtitle())
        self.assertIn("09:00 — 10:30", block._session_rows[0].get_title())
        self.assertIn("14:00", block._session_rows[1].get_title())
        self.assertIn(_("still active"), block._session_rows[1].get_title())


if __name__ == "__main__":
    unittest.main()
