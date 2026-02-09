"""
GUI module for SortMeOut.

Structure:
    - main_window.py: Primary menu bar app (PyInstaller entry point)
    - app.py: pip-installable GUI entry point (sortmeout-gui command)
    - chat_window.py: Premium AI chat interface
    - rule_editor.py: Rule creation/editing window
"""


def __getattr__(name):
    """Lazy imports to avoid pulling heavy GUI deps unless needed."""
    if name == "main":
        from sortmeout.gui.app import main

        return main
    if name == "MenuBarApp":
        from sortmeout.gui.app import MenuBarApp

        return MenuBarApp
    if name == "show_chat_window":
        from sortmeout.gui.chat_window import show_chat_window

        return show_chat_window
    if name == "show_rule_editor":
        from sortmeout.gui.rule_editor import show_rule_editor

        return show_rule_editor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    # Entry points
    "main",
    "MenuBarApp",
    # Windows
    "show_chat_window",
    "show_rule_editor",
]
