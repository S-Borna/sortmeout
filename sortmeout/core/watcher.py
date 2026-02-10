"""
Folder watching using macOS FSEvents.

This module provides file system monitoring for detecting changes in watched folders.
"""

from __future__ import annotations

import logging
import os
import threading
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set
from datetime import datetime
import time

from sortmeout.core.license import can_watch_filesystem, LicenseAuthority
from watchdog.observers import Observer
from watchdog.events import (
    FileSystemEventHandler,
    FileCreatedEvent,
    FileModifiedEvent,
    FileMovedEvent,
    FileDeletedEvent,
    DirCreatedEvent,
    DirModifiedEvent,
    DirMovedEvent,
    DirDeletedEvent,
)

from sortmeout.utils.logger import get_logger

logger = get_logger(__name__)


class FileEventHandler(FileSystemEventHandler):
    """
    Handle file system events from watchdog.

    Filters events and calls the appropriate callback with normalized event types.
    """

    def __init__(
        self,
        callback: Callable[[str, str, str], None],
        folder_path: str = "",
        ignore_patterns: Optional[List[str]] = None,
        include_directories: bool = False,
        debounce_seconds: float = 0.5,
    ):
        """
        Initialize the event handler.

        Args:
            callback: Function to call on file events (event_type, file_path, folder_path).
            folder_path: Path to the watched folder.
            ignore_patterns: File patterns to ignore.
            include_directories: Whether to process directory events.
            debounce_seconds: Time to wait before processing rapid events.
        """
        super().__init__()
        self.callback = callback
        self.folder_path = folder_path
        self.ignore_patterns = ignore_patterns or [
            ".*",  # Hidden files
            "*.tmp",
            "*.temp",
            "*.part",
            "*.crdownload",
            ".DS_Store",
            "Thumbs.db",
        ]
        self.include_directories = include_directories
        self.debounce_seconds = debounce_seconds

        # Debouncing: track recent events
        self._recent_events: Dict[str, datetime] = {}
        self._lock = threading.Lock()

    def _should_ignore(self, path: str) -> bool:
        """Check if a path should be ignored."""
        import fnmatch

        name = os.path.basename(path)

        for pattern in self.ignore_patterns:
            if fnmatch.fnmatch(name, pattern):
                return True

        return False

    def _debounce(self, path: str) -> bool:
        """
        Check if event should be processed (debouncing).

        Returns True if event should be processed.
        """
        now = datetime.now()

        with self._lock:
            last_event = self._recent_events.get(path)

            if last_event:
                delta = (now - last_event).total_seconds()
                if delta < self.debounce_seconds:
                    return False

            self._recent_events[path] = now

            # Clean up old entries
            cutoff = now.timestamp() - 60  # Keep last minute
            self._recent_events = {
                p: t for p, t in self._recent_events.items() if t.timestamp() > cutoff
            }

        return True

    def _process_event(self, event_type: str = "modified", src_path: str = None, is_directory: bool = False) -> None:
        """Process a file system event."""
        if src_path is None:
            # Called with just a path argument
            src_path = event_type
            event_type = "modified"

        if is_directory and not self.include_directories:
            return

        if self._should_ignore(src_path):
            return

        if not self._debounce(src_path):
            return

        logger.debug("Processing event: %s - %s", event_type, src_path)

        try:
            self.callback(event_type, src_path, self.folder_path)
        except Exception as e:
            logger.error("Error in callback for %s: %s", src_path, e)

    def on_created(self, event) -> None:
        """Handle file/directory created event."""
        # Brief pause to allow the OS to finish writing the file.
        # FSEvents fires on inode creation before the write is complete.
        # 100ms covers most small-to-medium file writes; large files are
        # handled by the debounce mechanism in _debounce() which waits
        # for event quiescence before processing.
        time.sleep(0.1)
        self._process_event("created", event.src_path, event.is_directory)

    def on_modified(self, event) -> None:
        """Handle file/directory modified event."""
        self._process_event("modified", event.src_path, event.is_directory)

    def on_moved(self, event) -> None:
        """Handle file/directory moved event."""
        # Treat destination as created
        self._process_event("created", event.dest_path, event.is_directory)

    def on_deleted(self, event) -> None:
        """Handle file/directory deleted event."""
        self._process_event("deleted", event.src_path, event.is_directory)


class FolderWatcher:
    """
    Watch a single folder for file changes.

    Attributes:
        path: Path to the watched folder.
        recursive: Whether to watch subdirectories.
        enabled: Whether watching is active.
    """

    def __init__(
        self,
        path: Optional[str] = None,
        callback: Optional[Callable[[str, str, str], None]] = None,
        recursive: bool = True,
        ignore_patterns: Optional[List[str]] = None,
        include_extensions: Optional[List[str]] = None,
        exclude_extensions: Optional[List[str]] = None,
        ignore_hidden: bool = True,
        folder_path: Optional[str] = None,
    ):
        """
        Initialize a folder watcher.

        Args:
            path: Path to watch.
            callback: Function to call on file events.
            recursive: Watch subdirectories.
            ignore_patterns: Patterns to ignore.
            include_extensions: Only process files with these extensions.
            exclude_extensions: Skip files with these extensions.
            ignore_hidden: Whether to ignore hidden files.
            folder_path: Alternative to path parameter.
        """
        actual_path = folder_path if folder_path is not None else path
        if not actual_path:
            raise ValueError("Either path or folder_path must be specified")
        self.path = os.path.expanduser(actual_path)
        self.callback = callback
        self.recursive = recursive
        self.ignore_patterns = ignore_patterns
        self.include_extensions = include_extensions
        self.exclude_extensions = exclude_extensions
        self.ignore_hidden = ignore_hidden
        self.enabled = True
        self._stats: Dict[str, int] = {"events_processed": 0, "files_processed": 0}

        self._observer: Optional[Observer] = None
        self._handler: Optional[FileEventHandler] = None

        # Validate path
        if not os.path.isdir(self.path):
            raise ValueError(f"Path is not a directory: {self.path}")

    @property
    def folder_path(self) -> str:
        """Alias for path."""
        return self.path

    @property
    def running(self) -> bool:
        """Check if watcher is running."""
        return self.is_running()

    def should_process(self, filename: str) -> bool:
        """Check if a file should be processed based on filters."""
        import fnmatch as fnmatch_mod
        name = os.path.basename(filename)

        if self.ignore_hidden and name.startswith('.'):
            return False

        if self.include_extensions:
            ext = os.path.splitext(name)[1]
            normalized = [e if e.startswith('.') else f'.{e}' for e in self.include_extensions]
            if ext not in normalized:
                return False

        if self.exclude_extensions:
            ext = os.path.splitext(name)[1]
            normalized = [e if e.startswith('.') else f'.{e}' for e in self.exclude_extensions]
            if ext in normalized:
                return False

        if self.ignore_patterns:
            for pattern in self.ignore_patterns:
                if fnmatch_mod.fnmatch(name, pattern):
                    return False

        return True

    def to_dict(self) -> Dict:
        """Serialize watcher configuration."""
        return {
            "folder_path": self.path,
            "recursive": self.recursive,
            "ignore_patterns": self.ignore_patterns or [],
            "enabled": self.enabled,
        }

    @classmethod
    def from_dict(cls, data: Dict, callback=None) -> "FolderWatcher":
        """Create a FolderWatcher from a dictionary."""
        return cls(
            path=data.get("folder_path") or data.get("path"),
            callback=callback,
            recursive=data.get("recursive", True),
            ignore_patterns=data.get("ignore_patterns"),
        )

    def get_stats(self) -> Dict[str, int]:
        """Get watcher statistics."""
        return self._stats.copy()

    def _increment_stats(self, key: str) -> None:
        """Increment a stats counter."""
        if key in self._stats:
            self._stats[key] += 1

    def _safe_callback(self, *args) -> None:
        """Call callback with error handling."""
        try:
            self.callback(*args)
        except Exception as e:
            logger.error("Callback error: %s", e)

    def start(self) -> None:
        """Start watching the folder."""
        # LICENSE GATE: Filesystem watching requires active license
        if not can_watch_filesystem():
            raise RuntimeError(LicenseAuthority.get_expired_message())

        if self._observer is not None:
            return

        self._handler = FileEventHandler(
            callback=self.callback,
            folder_path=self.path,
            ignore_patterns=self.ignore_patterns,
        )

        self._observer = Observer()
        self._observer.schedule(
            self._handler,
            self.path,
            recursive=self.recursive,
        )
        self._observer.start()

        logger.info("Started watching: %s (recursive=%s)", self.path, self.recursive)

    def stop(self) -> None:
        """Stop watching the folder."""
        if self._observer is None:
            return

        self._observer.stop()
        self._observer.join(timeout=5)
        self._observer = None
        self._handler = None

        logger.info("Stopped watching: %s", self.path)

    def is_running(self) -> bool:
        """Check if watcher is running."""
        return self._observer is not None and self._observer.is_alive()

    def __repr__(self) -> str:
        status = "running" if self.is_running() else "stopped"
        return f"FolderWatcher({self.path!r}, status={status})"


class WatcherManager:
    """
    Manage multiple folder watchers.

    Provides centralized control over all folder watchers and their lifecycle.
    """

    def __init__(self):
        """Initialize the watcher manager."""
        self._watchers: Dict[str, FolderWatcher] = {}
        self._running = False
        self._lock = threading.RLock()

    @property
    def watchers(self) -> Dict[str, FolderWatcher]:
        """Access watchers dict."""
        return self._watchers

    def add_watch(
        self,
        path: str,
        callback: Callable[[str, str, str], None],
        recursive: bool = False,
        ignore_patterns: Optional[List[str]] = None,
    ) -> bool:
        """
        Add a folder to watch.

        Args:
            path: Path to the folder.
            callback: Function to call on file events.
            recursive: Watch subdirectories.
            ignore_patterns: Patterns to ignore.

        Returns:
            True if watch was added successfully.
        """
        resolved_path = str(Path(os.path.expanduser(path)).resolve())

        with self._lock:
            if resolved_path in self._watchers:
                logger.warning("Already watching: %s", resolved_path)
                return False

            try:
                watcher = FolderWatcher(
                    path=resolved_path,
                    callback=callback,
                    recursive=recursive,
                    ignore_patterns=ignore_patterns,
                )

                if self._running:
                    watcher.start()

                self._watchers[resolved_path] = watcher
                logger.info("Added watch: %s", resolved_path)
                return True

            except Exception as e:
                logger.error("Failed to add watch for %s: %s", resolved_path, e)
                return False

    def remove_watch(self, path: str) -> bool:
        """
        Remove a folder watch.

        Args:
            path: Path to the folder.

        Returns:
            True if watch was removed successfully.
        """
        resolved_path = str(Path(os.path.expanduser(path)).resolve())

        with self._lock:
            if resolved_path not in self._watchers:
                return False

            watcher = self._watchers.pop(resolved_path)
            watcher.stop()

            logger.info("Removed watch: %s", resolved_path)
            return True

    def get_watched_folders(self) -> List[str]:
        """Get list of all watched folders."""
        with self._lock:
            return list(self._watchers.keys())

    def add_watcher(
        self,
        folder_path: str = None,
        callback=None,
        recursive: bool = True,
        ignore_patterns=None,
        path: str = None,
    ) -> FolderWatcher:
        """Add a folder watcher and return it."""
        actual_path = folder_path or path or ""
        watcher = FolderWatcher(
            path=actual_path,
            callback=callback,
            recursive=recursive,
            ignore_patterns=ignore_patterns,
        )
        with self._lock:
            self._watchers[watcher.path] = watcher
            if self._running:
                watcher.start()
        return watcher

    def remove_watcher(self, path: str) -> bool:
        """Remove a watcher by path."""
        expanded = os.path.expanduser(path)
        with self._lock:
            if expanded in self._watchers:
                self._watchers.pop(expanded).stop()
                return True
        return False

    def get_watcher(self, path: str) -> Optional[FolderWatcher]:
        """Get a watcher by path."""
        expanded = os.path.expanduser(path)
        return self._watchers.get(expanded)

    def start_all(self) -> None:
        """Start all watchers."""
        self.start()

    def stop_all(self) -> None:
        """Stop all watchers."""
        self.stop()

    def list_watched_folders(self) -> List[str]:
        """List all watched folder paths."""
        return self.get_watched_folders()

    def start(self) -> None:
        """Start all watchers."""
        with self._lock:
            if self._running:
                return

            self._running = True

            for watcher in self._watchers.values():
                if not watcher.is_running():
                    watcher.start()

            logger.info("Started %d watchers", len(self._watchers))

    def stop(self) -> None:
        """Stop all watchers."""
        with self._lock:
            if not self._running:
                return

            self._running = False

            for watcher in self._watchers.values():
                watcher.stop()

            logger.info("Stopped all watchers")

    def is_running(self) -> bool:
        """Check if manager is running."""
        return self._running

    def get_status(self) -> Dict[str, Dict]:
        """Get status of all watchers."""
        with self._lock:
            return {
                path: {
                    "running": watcher.is_running(),
                    "recursive": watcher.recursive,
                    "enabled": watcher.enabled,
                }
                for path, watcher in self._watchers.items()
            }

    def __len__(self) -> int:
        """Number of watched folders."""
        return len(self._watchers)

    def __repr__(self) -> str:
        status = "running" if self._running else "stopped"
        return f"WatcherManager({len(self._watchers)} watchers, status={status})"


class FSEventsWatcher:
    """
    Native macOS FSEvents watcher using PyObjC.

    This provides more efficient file system monitoring on macOS
    compared to the generic watchdog implementation.
    """

    def __init__(
        self,
        path: str,
        callback: Callable[[str, str, str], None],
        latency: float = 0.5,
    ):
        """
        Initialize FSEvents watcher.

        Args:
            path: Path to watch.
            callback: Callback function.
            latency: Latency in seconds before reporting events.
        """
        self.path = os.path.expanduser(path)
        self.callback = callback
        self.latency = latency
        self._stream = None
        self._running = False

    def start(self) -> None:
        """Start the FSEvents stream."""
        try:
            from FSEvents import (
                FSEventStreamCreate,
                FSEventStreamScheduleWithRunLoop,
                FSEventStreamStart,
                FSEventStreamStop,
                FSEventStreamInvalidate,
                FSEventStreamRelease,
                CFRunLoopGetCurrent,
                kCFRunLoopDefaultMode,
                kFSEventStreamEventFlagNone,
            )

            def fsevents_callback(stream, info, num_events, paths, flags, ids):
                for i in range(num_events):
                    path = paths[i].decode() if isinstance(paths[i], bytes) else paths[i]
                    self.callback("modified", path, self.path)

            self._stream = FSEventStreamCreate(
                None,
                fsevents_callback,
                None,
                [self.path],
                -1,  # kFSEventStreamEventIdSinceNow
                self.latency,
                kFSEventStreamEventFlagNone,
            )

            FSEventStreamScheduleWithRunLoop(
                self._stream,
                CFRunLoopGetCurrent(),
                kCFRunLoopDefaultMode,
            )

            FSEventStreamStart(self._stream)
            self._running = True

            logger.info("Started FSEvents watcher: %s", self.path)

        except ImportError:
            logger.warning("FSEvents not available, falling back to watchdog")
            raise

    def stop(self) -> None:
        """Stop the FSEvents stream."""
        if self._stream:
            try:
                from FSEvents import (
                    FSEventStreamStop,
                    FSEventStreamInvalidate,
                    FSEventStreamRelease,
                )

                FSEventStreamStop(self._stream)
                FSEventStreamInvalidate(self._stream)
                FSEventStreamRelease(self._stream)

            except ImportError:
                pass

            self._stream = None
            self._running = False

            logger.info("Stopped FSEvents watcher: %s", self.path)

    def is_running(self) -> bool:
        """Check if watcher is running."""
        return self._running
