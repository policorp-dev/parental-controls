"""Entry point for big-parental-controls."""

import os
import sys


def _ensure_dev_path() -> None:
    """If running from the source tree, prepend src/ to sys.path so the
    local package is always imported instead of a system-installed copy."""
    here = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.normpath(os.path.join(here, ".."))
    # Verify this really is the source tree (contains big_parental_controls package)
    marker = os.path.join(src_dir, "big_parental_controls", "__init__.py")
    if os.path.isfile(marker) and src_dir not in sys.path:
        sys.path.insert(0, src_dir)


_ensure_dev_path()

from big_parental_controls.utils.i18n import setup_i18n

setup_i18n()

from big_parental_controls.app import ParentalControlsApp


def main() -> int:
    app = ParentalControlsApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
