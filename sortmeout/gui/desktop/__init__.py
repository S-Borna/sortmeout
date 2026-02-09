"""SortMeOut Desktop — Full desktop application."""

try:
    from sortmeout.gui.desktop.app import DesktopApp
except ImportError:
    DesktopApp = None  # PyObjC/WebKit not available

__all__ = ["DesktopApp"]
