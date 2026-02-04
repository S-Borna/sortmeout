"""
Action definitions for file operations.

Actions define what operations to perform on files that match rule conditions.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
import re


class ActionType(Enum):
    """Available action types."""
    # File operations
    MOVE = "move"
    COPY = "copy"
    RENAME = "rename"
    DELETE = "delete"
    TRASH = "trash"  # Move to Trash

    # Archive operations
    ARCHIVE = "archive"  # Create archive
    EXTRACT = "extract"  # Extract archive

    # macOS operations
    ADD_TAGS = "add_tags"
    REMOVE_TAGS = "remove_tags"
    SET_TAGS = "set_tags"  # Replace all tags
    SET_COMMENT = "set_comment"  # Finder comment
    SET_LABEL = "set_label"  # Finder color label
    REVEAL_IN_FINDER = "reveal_in_finder"

    # Application operations
    OPEN_WITH = "open_with"
    IMPORT_TO_PHOTOS = "import_to_photos"
    IMPORT_TO_MUSIC = "import_to_music"

    # Script operations
    RUN_SHELL = "run_shell"
    RUN_APPLESCRIPT = "run_applescript"
    RUN_AUTOMATOR = "run_automator"
    RUN_SHORTCUT = "run_shortcut"

    # Notification operations
    NOTIFY = "notify"

    # Utility operations
    NOTHING = "nothing"  # Do nothing (for testing)
    STOP = "stop"  # Stop processing rules
    CONTINUE = "continue"  # Continue processing (opposite of default)


class ArchiveFormat(Enum):
    """Archive format options."""
    ZIP = "zip"
    TAR = "tar"
    TAR_GZ = "tar.gz"
    TAR_BZ2 = "tar.bz2"


class FinderLabel(Enum):
    """macOS Finder color labels."""
    NONE = 0
    GRAY = 1
    GREEN = 2
    PURPLE = 3
    BLUE = 4
    YELLOW = 5
    RED = 6
    ORANGE = 7


@dataclass
class ActionResult:
    """
    Result of an action execution.

    Attributes:
        success: Whether the action succeeded.
        action_type: Type of action that was executed.
        source_path: Original file path.
        destination_path: New file path (if applicable).
        message: Human-readable result message.
        error: Error message if action failed.
        metadata: Additional metadata about the action.
    """
    success: bool
    action_type: ActionType
    source_path: str
    destination_path: Optional[str] = None
    message: str = ""
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def __str__(self) -> str:
        status = "✓" if self.success else "✗"
        return f"[{status}] {self.action_type.value}: {self.message}"


@dataclass
class Action:
    """
    An action to perform on a matching file.

    Attributes:
        action_type: Type of action to perform.
        params: Parameters for the action.
        enabled: Whether the action is active.
        stop_on_error: Stop rule processing if this action fails.
        id: Unique identifier.

    Example:
        >>> action = Action("move", destination="~/Documents/PDFs")
        >>> result = action.execute("/path/to/file.pdf", {})
    """

    action_type: str | ActionType
    params: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    stop_on_error: bool = True
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __init__(
        self,
        action_type: str | ActionType,
        enabled: bool = True,
        stop_on_error: bool = True,
        id: Optional[str] = None,
        **kwargs: Any
    ):
        """
        Initialize an action.

        Args:
            action_type: Type of action.
            enabled: Whether action is enabled.
            stop_on_error: Stop processing on error.
            id: Unique identifier.
            **kwargs: Action-specific parameters.
        """
        if isinstance(action_type, str):
            self.action_type = ActionType(action_type)
        else:
            self.action_type = action_type

        self.params = kwargs
        self.enabled = enabled
        self.stop_on_error = stop_on_error
        self.id = id or str(uuid.uuid4())

    def execute(
        self,
        file_path: str,
        file_info: Dict[str, Any],
        preview: bool = False,
    ) -> ActionResult:
        """
        Execute the action on a file.

        Args:
            file_path: Path to the file.
            file_info: Dictionary containing file attributes.
            preview: If True, don't actually perform the action.

        Returns:
            ActionResult with execution status.
        """
        if not self.enabled:
            return ActionResult(
                success=True,
                action_type=self.action_type,
                source_path=file_path,
                message="Action disabled, skipped",
            )

        # Expand any variables in parameters
        expanded_params = self._expand_params(file_path, file_info)

        if preview:
            return ActionResult(
                success=True,
                action_type=self.action_type,
                source_path=file_path,
                destination_path=expanded_params.get("destination"),
                message=f"[PREVIEW] Would execute {self.action_type.value}",
                metadata={"params": expanded_params},
            )

        # Dispatch to specific handler
        handler = self._get_handler()
        if handler:
            try:
                return handler(file_path, expanded_params, file_info)
            except Exception as e:
                return ActionResult(
                    success=False,
                    action_type=self.action_type,
                    source_path=file_path,
                    error=str(e),
                    message=f"Action failed: {e}",
                )

        return ActionResult(
            success=False,
            action_type=self.action_type,
            source_path=file_path,
            error=f"No handler for action type: {self.action_type}",
        )

    def _get_handler(self) -> Optional[Callable]:
        """Get the handler function for this action type."""
        handlers = {
            ActionType.MOVE: self._do_move,
            ActionType.COPY: self._do_copy,
            ActionType.RENAME: self._do_rename,
            ActionType.DELETE: self._do_delete,
            ActionType.TRASH: self._do_trash,
            ActionType.ARCHIVE: self._do_archive,
            ActionType.ADD_TAGS: self._do_add_tags,
            ActionType.REMOVE_TAGS: self._do_remove_tags,
            ActionType.SET_TAGS: self._do_set_tags,
            ActionType.SET_COMMENT: self._do_set_comment,
            ActionType.OPEN_WITH: self._do_open_with,
            ActionType.RUN_SHELL: self._do_run_shell,
            ActionType.RUN_APPLESCRIPT: self._do_run_applescript,
            ActionType.RUN_SHORTCUT: self._do_run_shortcut,
            ActionType.NOTIFY: self._do_notify,
            ActionType.NOTHING: self._do_nothing,
            ActionType.REVEAL_IN_FINDER: self._do_reveal_in_finder,
        }
        return handlers.get(self.action_type)

    def _expand_params(self, file_path: str, file_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Expand variables in parameters.

        Variables:
        - {name}: File name without extension
        - {extension}: File extension
        - {full_name}: Full file name
        - {parent}: Parent folder name
        - {date}: Current date (YYYY-MM-DD)
        - {time}: Current time (HH-MM-SS)
        - {datetime}: Current datetime
        - {year}, {month}, {day}: Date components
        - {created_date}, {modified_date}: File dates
        - {size}: File size
        - {counter}: Auto-incrementing counter
        """
        path = Path(file_path)
        now = datetime.now()

        variables = {
            "name": path.stem,
            "extension": path.suffix.lstrip("."),
            "full_name": path.name,
            "parent": path.parent.name,
            "path": str(path.parent),
            "date": now.strftime("%Y-%m-%d"),
            "time": now.strftime("%H-%M-%S"),
            "datetime": now.strftime("%Y-%m-%d_%H-%M-%S"),
            "year": now.strftime("%Y"),
            "month": now.strftime("%m"),
            "day": now.strftime("%d"),
            "hour": now.strftime("%H"),
            "minute": now.strftime("%M"),
        }

        # Add file_info variables
        for key, value in file_info.items():
            if isinstance(value, datetime):
                variables[f"{key}_date"] = value.strftime("%Y-%m-%d")
                variables[f"{key}_year"] = value.strftime("%Y")
                variables[f"{key}_month"] = value.strftime("%m")
                variables[f"{key}_day"] = value.strftime("%d")
            elif isinstance(value, (str, int, float)):
                variables[key] = str(value)

        # Expand variables in string parameters
        expanded = {}
        for key, value in self.params.items():
            if isinstance(value, str):
                expanded_value = value
                for var_name, var_value in variables.items():
                    expanded_value = expanded_value.replace(f"{{{var_name}}}", str(var_value))
                # Expand user home directory
                expanded_value = os.path.expanduser(expanded_value)
                expanded[key] = expanded_value
            else:
                expanded[key] = value

        return expanded

    # Action handlers

    def _do_move(self, file_path: str, params: Dict[str, Any], file_info: Dict[str, Any]) -> ActionResult:
        """Move file to destination."""
        destination = params.get("destination")
        if not destination:
            return ActionResult(
                success=False,
                action_type=self.action_type,
                source_path=file_path,
                error="No destination specified",
            )

        dest_path = Path(destination)

        # If destination is a directory, move file into it
        if dest_path.is_dir() or not dest_path.suffix:
            dest_path.mkdir(parents=True, exist_ok=True)
            dest_path = dest_path / Path(file_path).name
        else:
            dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Handle conflicts
        dest_path = self._handle_conflict(dest_path, params.get("if_exists", "rename"))

        shutil.move(file_path, dest_path)

        return ActionResult(
            success=True,
            action_type=self.action_type,
            source_path=file_path,
            destination_path=str(dest_path),
            message=f"Moved to {dest_path}",
        )

    def _do_copy(self, file_path: str, params: Dict[str, Any], file_info: Dict[str, Any]) -> ActionResult:
        """Copy file to destination."""
        destination = params.get("destination")
        if not destination:
            return ActionResult(
                success=False,
                action_type=self.action_type,
                source_path=file_path,
                error="No destination specified",
            )

        dest_path = Path(destination)

        if dest_path.is_dir() or not dest_path.suffix:
            dest_path.mkdir(parents=True, exist_ok=True)
            dest_path = dest_path / Path(file_path).name
        else:
            dest_path.parent.mkdir(parents=True, exist_ok=True)

        dest_path = self._handle_conflict(dest_path, params.get("if_exists", "rename"))

        shutil.copy2(file_path, dest_path)

        return ActionResult(
            success=True,
            action_type=self.action_type,
            source_path=file_path,
            destination_path=str(dest_path),
            message=f"Copied to {dest_path}",
        )

    def _do_rename(self, file_path: str, params: Dict[str, Any], file_info: Dict[str, Any]) -> ActionResult:
        """Rename file."""
        new_name = params.get("new_name") or params.get("pattern")
        if not new_name:
            return ActionResult(
                success=False,
                action_type=self.action_type,
                source_path=file_path,
                error="No new name specified",
            )

        path = Path(file_path)
        new_path = path.parent / new_name
        new_path = self._handle_conflict(new_path, params.get("if_exists", "rename"))

        path.rename(new_path)

        return ActionResult(
            success=True,
            action_type=self.action_type,
            source_path=file_path,
            destination_path=str(new_path),
            message=f"Renamed to {new_path.name}",
        )

    def _do_delete(self, file_path: str, params: Dict[str, Any], file_info: Dict[str, Any]) -> ActionResult:
        """Delete file permanently."""
        path = Path(file_path)

        if params.get("confirm", True) and not params.get("force", False):
            # In a real implementation, we might prompt for confirmation
            pass

        if path.is_file():
            path.unlink()
        elif path.is_dir():
            shutil.rmtree(path)

        return ActionResult(
            success=True,
            action_type=self.action_type,
            source_path=file_path,
            message="Deleted permanently",
        )

    def _do_trash(self, file_path: str, params: Dict[str, Any], file_info: Dict[str, Any]) -> ActionResult:
        """Move file to Trash."""
        try:
            # Use macOS-specific trash command
            subprocess.run(
                ["osascript", "-e", f'tell application "Finder" to delete POSIX file "{file_path}"'],
                check=True,
                capture_output=True,
            )
            return ActionResult(
                success=True,
                action_type=self.action_type,
                source_path=file_path,
                message="Moved to Trash",
            )
        except subprocess.CalledProcessError as e:
            return ActionResult(
                success=False,
                action_type=self.action_type,
                source_path=file_path,
                error=f"Failed to move to Trash: {e}",
            )

    def _do_archive(self, file_path: str, params: Dict[str, Any], file_info: Dict[str, Any]) -> ActionResult:
        """Create archive from file."""
        format_str = params.get("format", "zip")
        destination = params.get("destination")

        path = Path(file_path)

        if destination:
            archive_path = Path(destination)
        else:
            archive_path = path.parent / f"{path.stem}.{format_str}"

        archive_path = self._handle_conflict(archive_path, params.get("if_exists", "rename"))

        if format_str == "zip":
            shutil.make_archive(str(archive_path.with_suffix("")), "zip", path.parent, path.name)
        elif format_str == "tar":
            shutil.make_archive(str(archive_path.with_suffix("")), "tar", path.parent, path.name)
        elif format_str == "tar.gz":
            shutil.make_archive(str(archive_path.with_suffix("")), "gztar", path.parent, path.name)
        elif format_str == "tar.bz2":
            shutil.make_archive(str(archive_path.with_suffix("")), "bztar", path.parent, path.name)

        # Delete original if requested
        if params.get("delete_original", False):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)

        return ActionResult(
            success=True,
            action_type=self.action_type,
            source_path=file_path,
            destination_path=str(archive_path),
            message=f"Archived to {archive_path}",
        )

    def _do_add_tags(self, file_path: str, params: Dict[str, Any], file_info: Dict[str, Any]) -> ActionResult:
        """Add macOS tags to file."""
        tags = params.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]

        if not tags:
            return ActionResult(
                success=False,
                action_type=self.action_type,
                source_path=file_path,
                error="No tags specified",
            )

        # Use xattr to add tags on macOS
        try:
            from sortmeout.macos.tags import add_tags
            add_tags(file_path, tags)
            return ActionResult(
                success=True,
                action_type=self.action_type,
                source_path=file_path,
                message=f"Added tags: {', '.join(tags)}",
                metadata={"tags": tags},
            )
        except ImportError:
            # Fallback to shell command
            tag_str = ",".join(tags)
            subprocess.run(
                ["tag", "-a", tag_str, file_path],
                check=True,
                capture_output=True,
            )
            return ActionResult(
                success=True,
                action_type=self.action_type,
                source_path=file_path,
                message=f"Added tags: {tag_str}",
                metadata={"tags": tags},
            )

    def _do_remove_tags(self, file_path: str, params: Dict[str, Any], file_info: Dict[str, Any]) -> ActionResult:
        """Remove macOS tags from file."""
        tags = params.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]

        try:
            from sortmeout.macos.tags import remove_tags
            remove_tags(file_path, tags)
            return ActionResult(
                success=True,
                action_type=self.action_type,
                source_path=file_path,
                message=f"Removed tags: {', '.join(tags)}",
                metadata={"tags": tags},
            )
        except ImportError:
            if tags:
                tag_str = ",".join(tags)
                subprocess.run(
                    ["tag", "-r", tag_str, file_path],
                    check=True,
                    capture_output=True,
                )
            return ActionResult(
                success=True,
                action_type=self.action_type,
                source_path=file_path,
                message=f"Removed tags: {', '.join(tags)}",
            )

    def _do_set_tags(self, file_path: str, params: Dict[str, Any], file_info: Dict[str, Any]) -> ActionResult:
        """Set macOS tags (replace all existing)."""
        tags = params.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]

        try:
            from sortmeout.macos.tags import set_tags
            set_tags(file_path, tags)
            return ActionResult(
                success=True,
                action_type=self.action_type,
                source_path=file_path,
                message=f"Set tags: {', '.join(tags)}",
                metadata={"tags": tags},
            )
        except ImportError:
            tag_str = ",".join(tags)
            subprocess.run(
                ["tag", "-s", tag_str, file_path],
                check=True,
                capture_output=True,
            )
            return ActionResult(
                success=True,
                action_type=self.action_type,
                source_path=file_path,
                message=f"Set tags: {tag_str}",
            )

    def _do_set_comment(self, file_path: str, params: Dict[str, Any], file_info: Dict[str, Any]) -> ActionResult:
        """Set Finder comment."""
        comment = params.get("comment", "")

        script = f'''
            tell application "Finder"
                set comment of (POSIX file "{file_path}" as alias) to "{comment}"
            end tell
        '''

        subprocess.run(["osascript", "-e", script], check=True, capture_output=True)

        return ActionResult(
            success=True,
            action_type=self.action_type,
            source_path=file_path,
            message=f"Set comment: {comment[:50]}...",
            metadata={"comment": comment},
        )

    def _do_open_with(self, file_path: str, params: Dict[str, Any], file_info: Dict[str, Any]) -> ActionResult:
        """Open file with application."""
        app = params.get("application") or params.get("app")
        if not app:
            # Open with default application
            subprocess.run(["open", file_path], check=True)
        else:
            subprocess.run(["open", "-a", app, file_path], check=True)

        return ActionResult(
            success=True,
            action_type=self.action_type,
            source_path=file_path,
            message=f"Opened with {app or 'default application'}",
        )

    def _do_run_shell(self, file_path: str, params: Dict[str, Any], file_info: Dict[str, Any]) -> ActionResult:
        """Run shell script."""
        script = params.get("script") or params.get("command")
        if not script:
            return ActionResult(
                success=False,
                action_type=self.action_type,
                source_path=file_path,
                error="No script specified",
            )

        # Set environment variables
        env = os.environ.copy()
        env["SORTMEOUT_FILE"] = file_path
        env["SORTMEOUT_NAME"] = Path(file_path).stem
        env["SORTMEOUT_EXTENSION"] = Path(file_path).suffix.lstrip(".")
        env["SORTMEOUT_FOLDER"] = str(Path(file_path).parent)

        result = subprocess.run(
            script,
            shell=True,
            env=env,
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return ActionResult(
                success=False,
                action_type=self.action_type,
                source_path=file_path,
                error=f"Script failed: {result.stderr}",
                metadata={"stdout": result.stdout, "stderr": result.stderr},
            )

        return ActionResult(
            success=True,
            action_type=self.action_type,
            source_path=file_path,
            message="Script executed successfully",
            metadata={"stdout": result.stdout},
        )

    def _do_run_applescript(self, file_path: str, params: Dict[str, Any], file_info: Dict[str, Any]) -> ActionResult:
        """Run AppleScript."""
        script = params.get("script")
        script_file = params.get("script_file")

        if script_file:
            result = subprocess.run(
                ["osascript", os.path.expanduser(script_file), file_path],
                capture_output=True,
                text=True,
            )
        elif script:
            # Replace placeholder with actual file path
            script = script.replace("{file}", file_path)
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
            )
        else:
            return ActionResult(
                success=False,
                action_type=self.action_type,
                source_path=file_path,
                error="No AppleScript specified",
            )

        if result.returncode != 0:
            return ActionResult(
                success=False,
                action_type=self.action_type,
                source_path=file_path,
                error=f"AppleScript failed: {result.stderr}",
            )

        return ActionResult(
            success=True,
            action_type=self.action_type,
            source_path=file_path,
            message="AppleScript executed",
            metadata={"output": result.stdout},
        )

    def _do_run_shortcut(self, file_path: str, params: Dict[str, Any], file_info: Dict[str, Any]) -> ActionResult:
        """Run Shortcuts workflow."""
        shortcut_name = params.get("shortcut") or params.get("name")
        if not shortcut_name:
            return ActionResult(
                success=False,
                action_type=self.action_type,
                source_path=file_path,
                error="No shortcut name specified",
            )

        result = subprocess.run(
            ["shortcuts", "run", shortcut_name, "-i", file_path],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            return ActionResult(
                success=False,
                action_type=self.action_type,
                source_path=file_path,
                error=f"Shortcut failed: {result.stderr}",
            )

        return ActionResult(
            success=True,
            action_type=self.action_type,
            source_path=file_path,
            message=f"Ran shortcut: {shortcut_name}",
        )

    def _do_notify(self, file_path: str, params: Dict[str, Any], file_info: Dict[str, Any]) -> ActionResult:
        """Send notification."""
        title = params.get("title", "SortMeOut")
        message = params.get("message", f"Processed: {Path(file_path).name}")
        sound = params.get("sound", "default")

        script = f'''
            display notification "{message}" with title "{title}" sound name "{sound}"
        '''

        subprocess.run(["osascript", "-e", script], check=True, capture_output=True)

        return ActionResult(
            success=True,
            action_type=self.action_type,
            source_path=file_path,
            message=f"Notification sent: {message}",
        )

    def _do_nothing(self, file_path: str, params: Dict[str, Any], file_info: Dict[str, Any]) -> ActionResult:
        """Do nothing (for testing or placeholders)."""
        return ActionResult(
            success=True,
            action_type=self.action_type,
            source_path=file_path,
            message="No action performed",
        )

    def _do_reveal_in_finder(self, file_path: str, params: Dict[str, Any], file_info: Dict[str, Any]) -> ActionResult:
        """Reveal file in Finder."""
        subprocess.run(["open", "-R", file_path], check=True)

        return ActionResult(
            success=True,
            action_type=self.action_type,
            source_path=file_path,
            message="Revealed in Finder",
        )

    def _handle_conflict(self, path: Path, strategy: str = "rename") -> Path:
        """
        Handle file name conflicts.

        Args:
            path: Target path.
            strategy: How to handle conflicts:
                - "rename": Add number suffix
                - "overwrite": Replace existing
                - "skip": Return original path (caller should check existence)

        Returns:
            Final path to use.
        """
        if strategy == "overwrite" or not path.exists():
            return path

        if strategy == "skip":
            return path

        # Rename strategy: add number suffix
        base = path.stem
        suffix = path.suffix
        parent = path.parent
        counter = 1

        while path.exists():
            path = parent / f"{base} ({counter}){suffix}"
            counter += 1

        return path

    def duplicate(self) -> "Action":
        """Create a copy of this action."""
        return Action(
            action_type=self.action_type,
            enabled=self.enabled,
            stop_on_error=self.stop_on_error,
            **self.params
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert action to dictionary for serialization."""
        return {
            "id": self.id,
            "action_type": self.action_type.value,
            "params": self.params,
            "enabled": self.enabled,
            "stop_on_error": self.stop_on_error,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Action":
        """Create an action from a dictionary."""
        return cls(
            id=data.get("id"),
            action_type=data["action_type"],
            enabled=data.get("enabled", True),
            stop_on_error=data.get("stop_on_error", True),
            **data.get("params", {}),
        )

    def __str__(self) -> str:
        """Human-readable representation."""
        status = "✓" if self.enabled else "✗"
        params_str = ", ".join(f"{k}={v!r}" for k, v in self.params.items())
        return f"[{status}] {self.action_type.value}({params_str})"


# Convenience functions for creating common actions

def move_to(destination: str, if_exists: str = "rename") -> Action:
    """Create a move action."""
    return Action("move", destination=destination, if_exists=if_exists)


def copy_to(destination: str, if_exists: str = "rename") -> Action:
    """Create a copy action."""
    return Action("copy", destination=destination, if_exists=if_exists)


def rename(pattern: str, if_exists: str = "rename") -> Action:
    """Create a rename action."""
    return Action("rename", new_name=pattern, if_exists=if_exists)


def delete(force: bool = False) -> Action:
    """Create a delete action."""
    return Action("delete", force=force)


def trash() -> Action:
    """Create a trash action."""
    return Action("trash")


def archive(format: str = "zip", delete_original: bool = False) -> Action:
    """Create an archive action."""
    return Action("archive", format=format, delete_original=delete_original)


def add_tags(*tags: str) -> Action:
    """Create an add tags action."""
    return Action("add_tags", tags=list(tags))


def notify(title: str = "SortMeOut", message: str = "{full_name} processed") -> Action:
    """Create a notification action."""
    return Action("notify", title=title, message=message)


def run_shell(script: str) -> Action:
    """Create a shell script action."""
    return Action("run_shell", script=script)


def open_with(application: str) -> Action:
    """Create an open with action."""
    return Action("open_with", application=application)
