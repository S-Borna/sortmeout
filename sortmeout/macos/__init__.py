"""
macOS-specific integrations for SortMeOut.
"""

from sortmeout.macos.tags import get_tags, set_tags, add_tags, remove_tags
from sortmeout.macos.spotlight import search_spotlight, get_metadata
from sortmeout.macos.trash import get_trash_info, empty_trash, TrashManager
from sortmeout.macos.system import (
    reveal_in_finder,
    quick_look,
    compress,
    decompress,
    send_notification,
    clipboard_copy,
    clipboard_paste,
    take_screenshot,
    toggle_dark_mode,
    get_dark_mode,
    set_volume,
    get_volume,
    toggle_mute,
    get_disk_space,
    get_battery_info,
    get_wifi_info,
    lock_screen,
    text_to_speech,
    kill_process,
    eject_volume,
    create_symlink,
    set_wallpaper,
    toggle_hidden_files,
    get_running_apps,
    get_folder_size,
    empty_trash_system,
    get_file_info_detailed,
    search_files,
)

__all__ = [
    # Tags
    "get_tags",
    "set_tags",
    "add_tags",
    "remove_tags",
    # Spotlight
    "search_spotlight",
    "get_metadata",
    # Trash
    "get_trash_info",
    "empty_trash",
    "TrashManager",
    # System
    "reveal_in_finder",
    "quick_look",
    "compress",
    "decompress",
    "send_notification",
    "clipboard_copy",
    "clipboard_paste",
    "take_screenshot",
    "toggle_dark_mode",
    "get_dark_mode",
    "set_volume",
    "get_volume",
    "toggle_mute",
    "get_disk_space",
    "get_battery_info",
    "get_wifi_info",
    "lock_screen",
    "text_to_speech",
    "kill_process",
    "eject_volume",
    "create_symlink",
    "set_wallpaper",
    "toggle_hidden_files",
    "get_running_apps",
    "get_folder_size",
    "empty_trash_system",
    "get_file_info_detailed",
    "search_files",
]
