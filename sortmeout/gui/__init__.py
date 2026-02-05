"""
GUI module for SortMeOut.

Structure:
    - main_window.py: Primary menu bar app (PyInstaller entry point)
    - app.py: pip-installable GUI entry point (sortmeout-gui command)
    - chat_window.py: Premium AI chat interface
    - rule_editor.py: Rule creation/editing window
"""

from sortmeout.gui.app import main, MenuBarApp
from sortmeout.gui.chat_window import show_chat_window
from sortmeout.gui.rule_editor import show_rule_editor

__all__ = [
    # Entry points
    "main",
    "MenuBarApp",
    # Windows
    "show_chat_window",
    "show_rule_editor",
]
