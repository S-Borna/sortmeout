"""
macOS Finder tags management.

Provides functions for reading and modifying Finder tags on files.
"""

from __future__ import annotations

import plistlib
import subprocess
from typing import List, Optional

from sortmeout.utils.logger import get_logger

logger = get_logger(__name__)

# Standard macOS tag colors
TAG_COLORS = {
    "none": 0,
    "gray": 1,
    "green": 2,
    "purple": 3,
    "blue": 4,
    "yellow": 5,
    "red": 6,
    "orange": 7,
}

# Reverse mapping
COLOR_NAMES = {v: k for k, v in TAG_COLORS.items()}


def get_tags(file_path: str) -> List[str]:
    """
    Get Finder tags for a file.

    Args:
        file_path: Path to the file.

    Returns:
        List of tag names.
    """
    try:
        result = subprocess.run(
            ["xattr", "-px", "com.apple.metadata:_kMDItemUserTags", file_path],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode != 0:
            return []

        # Parse hex output to binary
        hex_data = result.stdout.replace(" ", "").replace("\n", "")
        binary_data = bytes.fromhex(hex_data)

        # Parse plist
        tags_data = plistlib.loads(binary_data)

        # Extract tag names (format: "name\ncolor_index")
        tags = []
        for tag in tags_data:
            if isinstance(tag, str):
                name = tag.split("\n")[0]
                tags.append(name)

        return tags

    except Exception as e:
        logger.debug("Failed to get tags for %s: %s", file_path, e)
        return []


def set_tags(file_path: str, tags: List[str]) -> bool:
    """
    Set Finder tags for a file (replaces all existing tags).

    Args:
        file_path: Path to the file.
        tags: List of tag names to set.

    Returns:
        True if successful.
    """
    try:
        if not tags:
            # Remove all tags
            subprocess.run(
                ["xattr", "-d", "com.apple.metadata:_kMDItemUserTags", file_path],
                capture_output=True,
                timeout=5,
            )
            return True

        # Create plist data
        tag_data = [f"{tag}\n0" for tag in tags]  # 0 = no color
        plist_data = plistlib.dumps(tag_data)

        # Convert to hex string for xattr
        hex_string = plist_data.hex()

        # Write using xattr
        result = subprocess.run(
            ["xattr", "-wx", "com.apple.metadata:_kMDItemUserTags", hex_string, file_path],
            capture_output=True,
            timeout=5,
        )

        return result.returncode == 0

    except Exception as e:
        logger.error("Failed to set tags for %s: %s", file_path, e)
        return False


def add_tags(file_path: str, tags: List[str]) -> bool:
    """
    Add tags to a file (preserves existing tags).

    Args:
        file_path: Path to the file.
        tags: List of tag names to add.

    Returns:
        True if successful.
    """
    existing = get_tags(file_path)
    new_tags = list(set(existing + tags))
    return set_tags(file_path, new_tags)


def remove_tags(file_path: str, tags: List[str]) -> bool:
    """
    Remove specific tags from a file.

    Args:
        file_path: Path to the file.
        tags: List of tag names to remove.

    Returns:
        True if successful.
    """
    existing = get_tags(file_path)
    new_tags = [t for t in existing if t not in tags]
    return set_tags(file_path, new_tags)


def has_tag(file_path: str, tag: str) -> bool:
    """
    Check if a file has a specific tag.

    Args:
        file_path: Path to the file.
        tag: Tag name to check.

    Returns:
        True if file has the tag.
    """
    tags = get_tags(file_path)
    return tag in tags


def clear_tags(file_path: str) -> bool:
    """
    Remove all tags from a file.

    Args:
        file_path: Path to the file.

    Returns:
        True if successful.
    """
    return set_tags(file_path, [])


def get_all_tags() -> List[str]:
    """
    Get all tags defined in the system.

    Returns:
        List of all tag names.
    """
    try:
        # Read from Finder preferences
        result = subprocess.run(
            ["defaults", "read", "com.apple.finder", "FavoriteTagNames"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if result.returncode == 0:
            # Parse the output (it's in plist format)
            import re
            tags = re.findall(r'"([^"]+)"', result.stdout)
            return tags
    except Exception as e:
        logger.debug("Failed to get all tags: %s", e)

    # Return default tags
    return ["Red", "Orange", "Yellow", "Green", "Blue", "Purple", "Gray"]


def _escape_applescript(s: str) -> str:
    """Escape a string for safe use inside AppleScript double-quotes."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def set_finder_comment(file_path: str, comment: str) -> bool:
    """
    Set Finder comment for a file.

    Args:
        file_path: Path to the file.
        comment: Comment to set.

    Returns:
        True if successful.
    """
    try:
        safe_path = _escape_applescript(file_path)
        safe_comment = _escape_applescript(comment)

        script = f'''
            tell application "Finder"
                set theFile to POSIX file "{safe_path}" as alias
                set comment of theFile to "{safe_comment}"
            end tell
        '''

        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            timeout=10,
        )

        return result.returncode == 0

    except Exception as e:
        logger.error("Failed to set Finder comment: %s", e)
        return False


def get_finder_comment(file_path: str) -> Optional[str]:
    """
    Get Finder comment for a file.

    Args:
        file_path: Path to the file.

    Returns:
        Comment string or None.
    """
    try:
        safe_path = _escape_applescript(file_path)

        script = f'''
            tell application "Finder"
                set theFile to POSIX file "{safe_path}" as alias
                get comment of theFile
            end tell
        '''

        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            return result.stdout.strip()
        return None

    except Exception as e:
        logger.debug("Failed to get Finder comment: %s", e)
        return None


def set_label_color(file_path: str, color: str | int) -> bool:
    """
    Set Finder label color for a file.

    Args:
        file_path: Path to the file.
        color: Color name or index (0-7).

    Returns:
        True if successful.
    """
    if isinstance(color, str):
        color_index = TAG_COLORS.get(color.lower(), 0)
    else:
        color_index = color

    try:
        safe_path = _escape_applescript(file_path)

        script = f'''
            tell application "Finder"
                set theFile to POSIX file "{safe_path}" as alias
                set label index of theFile to {color_index}
            end tell
        '''

        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            timeout=10,
        )

        return result.returncode == 0

    except Exception as e:
        logger.error("Failed to set label color: %s", e)
        return False
