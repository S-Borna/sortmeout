"""
macOS Trash management.

Provides functions for managing the Trash and implementing App Sweep functionality.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from sortmeout.utils.logger import get_logger

logger = get_logger(__name__)


def _escape_applescript(s: str) -> str:
    """Escape a string for safe use inside AppleScript double-quoted strings."""
    return s.replace('\\', '\\\\').replace('"', '\\"')


@dataclass
class TrashItem:
    """Information about an item in the Trash."""
    path: str
    original_path: str
    name: str
    size: int
    deleted_date: datetime
    kind: str

    @property
    def age_days(self) -> int:
        """Days since item was deleted."""
        return (datetime.now() - self.deleted_date).days


@dataclass
class TrashInfo:
    """Overall Trash statistics."""
    item_count: int
    total_size: int
    oldest_item_date: Optional[datetime]
    newest_item_date: Optional[datetime]
    items: List[TrashItem]

    @property
    def size_human(self) -> str:
        """Human-readable size."""
        size = self.total_size
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} PB"


def get_trash_path() -> Path:
    """Get the user's Trash directory path."""
    return Path.home() / ".Trash"


def get_trash_info() -> TrashInfo:
    """
    Get information about the Trash contents.

    Returns:
        TrashInfo with statistics and item list.
    """
    trash_path = get_trash_path()
    items = []
    total_size = 0
    oldest_date = None
    newest_date = None

    if not trash_path.exists():
        return TrashInfo(
            item_count=0,
            total_size=0,
            oldest_item_date=None,
            newest_item_date=None,
            items=[],
        )

    for entry in trash_path.iterdir():
        try:
            stat = entry.stat()

            # Get size (recursively for directories)
            if entry.is_dir():
                size = sum(f.stat().st_size for f in entry.rglob("*") if f.is_file())
            else:
                size = stat.st_size

            total_size += size

            # Get deletion date from .DS_Store or use modification time
            deleted_date = datetime.fromtimestamp(stat.st_mtime)

            # Update date range
            if oldest_date is None or deleted_date < oldest_date:
                oldest_date = deleted_date
            if newest_date is None or deleted_date > newest_date:
                newest_date = deleted_date

            # Determine kind
            kind = "Folder" if entry.is_dir() else "File"

            items.append(TrashItem(
                path=str(entry),
                original_path="",  # Would need .Trashes metadata
                name=entry.name,
                size=size,
                deleted_date=deleted_date,
                kind=kind,
            ))

        except (PermissionError, OSError) as e:
            logger.debug("Error reading trash item %s: %s", entry, e)
            continue

    return TrashInfo(
        item_count=len(items),
        total_size=total_size,
        oldest_item_date=oldest_date,
        newest_item_date=newest_date,
        items=items,
    )


def empty_trash(secure: bool = False) -> bool:
    """
    Empty the Trash.

    Args:
        secure: If True, securely delete files (slower).

    Returns:
        True if successful.
    """
    try:
        if secure:
            script = '''
                tell application "Finder"
                    empty trash with security
                end tell
            '''
        else:
            script = '''
                tell application "Finder"
                    empty trash
                end tell
            '''

        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            timeout=60,
        )

        if result.returncode == 0:
            logger.info("Trash emptied")
            return True
        else:
            logger.error("Failed to empty trash: %s", result.stderr)
            return False

    except Exception as e:
        logger.error("Error emptying trash: %s", e)
        return False


def delete_old_trash_items(max_age_days: int) -> List[str]:
    """
    Delete items from Trash older than specified days.

    Args:
        max_age_days: Maximum age in days.

    Returns:
        List of deleted item names.
    """
    trash_info = get_trash_info()
    cutoff = datetime.now() - timedelta(days=max_age_days)
    deleted = []

    for item in trash_info.items:
        if item.deleted_date < cutoff:
            try:
                path = Path(item.path)
                if path.is_dir():
                    import shutil
                    shutil.rmtree(path)
                else:
                    path.unlink()
                deleted.append(item.name)
                logger.info("Deleted old trash item: %s", item.name)
            except Exception as e:
                logger.error("Failed to delete %s: %s", item.name, e)

    return deleted


def trim_trash_to_size(max_size_bytes: int) -> List[str]:
    """
    Trim Trash to maximum size by removing oldest items first.

    Args:
        max_size_bytes: Maximum total size in bytes.

    Returns:
        List of deleted item names.
    """
    trash_info = get_trash_info()

    if trash_info.total_size <= max_size_bytes:
        return []

    # Sort by date (oldest first)
    items_by_date = sorted(trash_info.items, key=lambda x: x.deleted_date)

    deleted = []
    current_size = trash_info.total_size

    for item in items_by_date:
        if current_size <= max_size_bytes:
            break

        try:
            path = Path(item.path)
            if path.is_dir():
                import shutil
                shutil.rmtree(path)
            else:
                path.unlink()

            current_size -= item.size
            deleted.append(item.name)
            logger.info("Deleted trash item to free space: %s", item.name)

        except Exception as e:
            logger.error("Failed to delete %s: %s", item.name, e)

    return deleted


class TrashManager:
    """
    Automatic trash management.

    Monitors and manages the Trash based on configured policies.
    """

    def __init__(
        self,
        max_age_days: int = 30,
        max_size_gb: float = 10.0,
        enabled: bool = True,
    ):
        """
        Initialize trash manager.

        Args:
            max_age_days: Maximum age for items.
            max_size_gb: Maximum total size in GB.
            enabled: Whether management is enabled.
        """
        self.max_age_days = max_age_days
        self.max_size_gb = max_size_gb
        self.max_size_bytes = int(max_size_gb * 1024 * 1024 * 1024)
        self.enabled = enabled

    def run_cleanup(self) -> Dict[str, Any]:
        """
        Run trash cleanup based on policies.

        Returns:
            Cleanup results.
        """
        if not self.enabled:
            return {"enabled": False, "deleted": []}

        results = {
            "deleted_by_age": [],
            "deleted_by_size": [],
            "before_size": 0,
            "after_size": 0,
        }

        # Get initial state
        before = get_trash_info()
        results["before_size"] = before.total_size

        # Delete old items
        if self.max_age_days > 0:
            results["deleted_by_age"] = delete_old_trash_items(self.max_age_days)

        # Trim to size
        if self.max_size_bytes > 0:
            results["deleted_by_size"] = trim_trash_to_size(self.max_size_bytes)

        # Get final state
        after = get_trash_info()
        results["after_size"] = after.total_size

        return results

    def get_status(self) -> Dict[str, Any]:
        """
        Get current trash status.

        Returns:
            Status information.
        """
        info = get_trash_info()

        return {
            "item_count": info.item_count,
            "total_size": info.total_size,
            "size_human": info.size_human,
            "oldest_item_age_days": (datetime.now() - info.oldest_item_date).days if info.oldest_item_date else 0,
            "over_size_limit": info.total_size > self.max_size_bytes,
            "has_old_items": info.oldest_item_date and (datetime.now() - info.oldest_item_date).days > self.max_age_days,
        }


# App Sweep functionality

def find_app_support_files(app_name: str) -> List[str]:
    """
    Find support files for an application.

    Args:
        app_name: Application name or bundle identifier.

    Returns:
        List of support file paths.
    """
    support_dirs = [
        Path.home() / "Library" / "Application Support",
        Path.home() / "Library" / "Preferences",
        Path.home() / "Library" / "Caches",
        Path.home() / "Library" / "Containers",
        Path.home() / "Library" / "Logs",
        Path.home() / "Library" / "Saved Application State",
        Path("/Library/Application Support"),
        Path("/Library/Preferences"),
    ]

    found_files = []

    # Normalize app name for matching
    app_name_lower = app_name.lower()
    # Remove .app extension if present
    if app_name_lower.endswith(".app"):
        app_name_lower = app_name_lower[:-4]

    for support_dir in support_dirs:
        if not support_dir.exists():
            continue

        try:
            for entry in support_dir.iterdir():
                entry_name = entry.name.lower()

                # Match by name
                if app_name_lower in entry_name:
                    found_files.append(str(entry))
                    continue

                # Match common patterns
                if any(pattern in entry_name for pattern in [
                    app_name_lower.replace(" ", ""),
                    app_name_lower.replace(" ", "-"),
                    app_name_lower.replace(" ", "_"),
                ]):
                    found_files.append(str(entry))

        except PermissionError:
            continue

    return found_files


def get_app_support_size(app_name: str) -> int:
    """
    Get total size of support files for an application.

    Args:
        app_name: Application name.

    Returns:
        Total size in bytes.
    """
    files = find_app_support_files(app_name)
    total = 0

    for file_path in files:
        path = Path(file_path)
        try:
            if path.is_dir():
                total += sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
            else:
                total += path.stat().st_size
        except (PermissionError, OSError):
            continue

    return total


def clean_app_support_files(app_name: str, to_trash: bool = True) -> List[str]:
    """
    Clean up support files for an application.

    Args:
        app_name: Application name.
        to_trash: Move to trash instead of deleting permanently.

    Returns:
        List of cleaned files.
    """
    files = find_app_support_files(app_name)
    cleaned = []

    for file_path in files:
        try:
            if to_trash:
                # Move to trash using Finder (with safe escaping)
                safe_path = _escape_applescript(file_path)
                script = f'''
                    tell application "Finder"
                        delete POSIX file "{safe_path}"
                    end tell
                '''
                subprocess.run(["osascript", "-e", script], capture_output=True, timeout=10)
            else:
                # Delete directly
                path = Path(file_path)
                if path.is_dir():
                    import shutil
                    shutil.rmtree(path)
                else:
                    path.unlink()

            cleaned.append(file_path)
            logger.info("Cleaned app support file: %s", file_path)

        except Exception as e:
            logger.error("Failed to clean %s: %s", file_path, e)

    return cleaned
