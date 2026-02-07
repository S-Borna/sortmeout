"""
Main Window for SortMeOut — thin shim.

Delegates to the unified menu bar app in gui/app.py.
This file exists for backward compatibility with PyInstaller spec
and direct-launch scenarios.
"""

from sortmeout.gui.app import main, MenuBarApp


def main():
    """Main entry point — delegates to unified app."""
    from sortmeout.gui.app import main as _main
    _main()


if __name__ == "__main__":
    main()
