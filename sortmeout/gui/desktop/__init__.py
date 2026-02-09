"""SortMeOut Desktop — Full desktop application."""


def __getattr__(name):
    """Lazy import to avoid double ObjC class registration."""
    if name == "DesktopApp":
        try:
            from sortmeout.gui.desktop.app import DesktopApp

            return DesktopApp
        except ImportError:
            return None
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["DesktopApp"]
