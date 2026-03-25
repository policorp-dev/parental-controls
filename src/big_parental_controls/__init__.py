"""BigLinux Parental Controls — keep children safe on this computer."""

__version__ = "1.0.0"

if __name__ == "__main__":
    import os
    import sys

    # Quando executado diretamente (python __init__.py), precisamos
    # adicionar src/ ao sys.path para que os imports do pacote funcionem.
    _here = os.path.dirname(os.path.abspath(__file__))
    _src_dir = os.path.normpath(os.path.join(_here, ".."))
    if _src_dir not in sys.path:
        sys.path.insert(0, _src_dir)

    from big_parental_controls.utils.i18n import setup_i18n
    setup_i18n()

    from big_parental_controls.app import ParentalControlsApp

    app = ParentalControlsApp()
    sys.exit(app.run(sys.argv))
