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
        folder_path: str,
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
                p: t for p, t in self._recent_events.items()
                if t.timestamp() > cutoff
            }

        return True

    def _process_event(self, event_type: str, src_path: str, is_directory: bool) -> None:
        """Process a file system event."""
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
        # Wait a bit for file to be fully written
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
        path: str,
        callback: Callable[[str, str, str], None],
        recursive: bool = False,
        ignore_patterns: Optional[List[str]] = None,
    ):
        """
        Initialize a folder watcher.

        Args:
            path: Path to watch.
            callback: Function to call on file events.
            recursive: Watch subdirectories.
            ignore_patterns: Patterns to ignore.
        """
        self.path = os.path.expanduser(path)
        self.callback = callback
        self.recursive = recursive
        self.ignore_patterns = ignore_patterns
        self.enabled = True

        self._observer: Optional[Observer] = None
        self._handler: Optional[FileEventHandler] = None

        # Validate path
        if not os.path.isdir(self.path):
            raise ValueError(f"Path is not a directory: {self.path}")

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
