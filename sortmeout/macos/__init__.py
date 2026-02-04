"""
macOS-specific integrations for SortMeOut.
"""

from sortmeout.macos.tags import get_tags, set_tags, add_tags, remove_tags
from sortmeout.macos.spotlight import search_spotlight, get_metadata
from sortmeout.macos.trash import get_trash_info, empty_trash, TrashManager

__all__ = [
    "get_tags",
    "set_tags",
    "add_tags",
    "remove_tags",
    "search_spotlight",
    "get_metadata",
    "get_trash_info",
    "empty_trash",
    "TrashManager",
]
