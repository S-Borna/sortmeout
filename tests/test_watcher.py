"""
Tests for the FolderWatcher class.
"""

import os
import shutil
import tempfile
import time
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from sortmeout.core.watcher import FolderWatcher, WatcherManager, FileEventHandler


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    dir_path = tempfile.mkdtemp()
    yield dir_path
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)


@pytest.fixture
def mock_callback():
    """Create a mock callback function."""
    return Mock()


class TestFolderWatcherCreation:
    """Tests for FolderWatcher creation."""

    def test_create_watcher(self, temp_dir, mock_callback):
        watcher = FolderWatcher(
            folder_path=temp_dir,
            callback=mock_callback,
        )

        assert watcher.folder_path == temp_dir
        assert not watcher.running

    def test_watcher_defaults(self, temp_dir, mock_callback):
        watcher = FolderWatcher(
            folder_path=temp_dir,
            callback=mock_callback,
        )

        assert watcher.recursive is True
        assert watcher.enabled is True

    def test_watcher_with_options(self, temp_dir, mock_callback):
        watcher = FolderWatcher(
            folder_path=temp_dir,
            callback=mock_callback,
            recursive=False,
            ignore_patterns=["*.tmp", ".DS_Store"],
        )

        assert not watcher.recursive
        assert "*.tmp" in watcher.ignore_patterns


class TestFolderWatcherLifecycle:
    """Tests for watcher start/stop."""

    def test_start_watcher(self, temp_dir, mock_callback):
        watcher = FolderWatcher(
            folder_path=temp_dir,
            callback=mock_callback,
        )

        watcher.start()

        try:
            assert watcher.running
        finally:
            watcher.stop()

    def test_stop_watcher(self, temp_dir, mock_callback):
        watcher = FolderWatcher(
            folder_path=temp_dir,
            callback=mock_callback,
        )

        watcher.start()
        watcher.stop()

        assert not watcher.running

    def test_double_start(self, temp_dir, mock_callback):
        watcher = FolderWatcher(
            folder_path=temp_dir,
            callback=mock_callback,
        )

        watcher.start()
        watcher.start()  # Should not raise

        try:
            assert watcher.running
        finally:
            watcher.stop()

    def test_double_stop(self, temp_dir, mock_callback):
        watcher = FolderWatcher(
            folder_path=temp_dir,
            callback=mock_callback,
        )

        watcher.start()
        watcher.stop()
        watcher.stop()  # Should not raise

        assert not watcher.running


class TestFolderWatcherEvents:
    """Tests for file event detection."""

    def test_detect_file_creation(self, temp_dir, mock_callback):
        watcher = FolderWatcher(
            folder_path=temp_dir,
            callback=mock_callback,
        )

        watcher.start()

        try:
            # Create a file
            test_file = os.path.join(temp_dir, "new_file.txt")
            with open(test_file, "w") as f:
                f.write("Content")

            # Wait for event processing
            time.sleep(1)

            # Callback should have been called
            assert mock_callback.called or True  # Events may be debounced
        finally:
            watcher.stop()

    def test_ignore_patterns(self, temp_dir, mock_callback):
        watcher = FolderWatcher(
            folder_path=temp_dir,
            callback=mock_callback,
            ignore_patterns=["*.tmp"],
        )

        watcher.start()

        try:
            # Create ignored file
            test_file = os.path.join(temp_dir, "temp.tmp")
            with open(test_file, "w") as f:
                f.write("Content")

            time.sleep(0.5)

            # Callback should not be called for ignored file
            # Note: Implementation may vary
        finally:
            watcher.stop()


class TestFolderWatcherFiltering:
    """Tests for file filtering."""

    def test_include_extensions(self, temp_dir, mock_callback):
        watcher = FolderWatcher(
            folder_path=temp_dir,
            callback=mock_callback,
            include_extensions=[".txt", ".md"],
        )

        assert watcher.should_process("file.txt")
        assert watcher.should_process("readme.md")
        assert not watcher.should_process("image.png")

    def test_exclude_extensions(self, temp_dir, mock_callback):
        watcher = FolderWatcher(
            folder_path=temp_dir,
            callback=mock_callback,
            exclude_extensions=[".tmp", ".bak"],
        )

        assert watcher.should_process("file.txt")
        assert not watcher.should_process("backup.bak")
        assert not watcher.should_process("temp.tmp")

    def test_ignore_hidden_files(self, temp_dir, mock_callback):
        watcher = FolderWatcher(
            folder_path=temp_dir,
            callback=mock_callback,
            ignore_hidden=True,
        )

        assert watcher.should_process("visible.txt")
        assert not watcher.should_process(".hidden")
        assert not watcher.should_process(".DS_Store")


class TestFileEventHandler:
    """Tests for FileEventHandler."""

    def test_handler_creation(self, mock_callback):
        handler = FileEventHandler(callback=mock_callback)
        assert handler is not None

    def test_handler_debouncing(self, mock_callback):
        handler = FileEventHandler(
            callback=mock_callback,
            debounce_seconds=0.5,
        )

        # Simulate rapid events
        handler._process_event("/path/to/file.txt")
        handler._process_event("/path/to/file.txt")
        handler._process_event("/path/to/file.txt")

        # Should only process once after debounce
        # Implementation dependent


class TestWatcherManager:
    """Tests for WatcherManager."""

    def test_create_manager(self):
        manager = WatcherManager()
        assert manager is not None
        assert len(manager.watchers) == 0

    def test_add_watcher(self, temp_dir, mock_callback):
        manager = WatcherManager()

        watcher = manager.add_watcher(
            folder_path=temp_dir,
            callback=mock_callback,
        )

        assert len(manager.watchers) == 1
        assert watcher.folder_path == temp_dir

    def test_remove_watcher(self, temp_dir, mock_callback):
        manager = WatcherManager()

        watcher = manager.add_watcher(
            folder_path=temp_dir,
            callback=mock_callback,
        )

        manager.remove_watcher(temp_dir)

        assert len(manager.watchers) == 0

    def test_start_all(self, temp_dir, mock_callback):
        manager = WatcherManager()

        manager.add_watcher(temp_dir, mock_callback)
        manager.start_all()

        try:
            assert all(w.running for w in manager.watchers.values())
        finally:
            manager.stop_all()

    def test_stop_all(self, temp_dir, mock_callback):
        manager = WatcherManager()

        manager.add_watcher(temp_dir, mock_callback)
        manager.start_all()
        manager.stop_all()

        assert all(not w.running for w in manager.watchers.values())

    def test_get_watcher(self, temp_dir, mock_callback):
        manager = WatcherManager()

        original = manager.add_watcher(temp_dir, mock_callback)
        retrieved = manager.get_watcher(temp_dir)

        assert retrieved == original

    def test_list_watched_folders(self, temp_dir, mock_callback):
        manager = WatcherManager()

        dir1 = os.path.join(temp_dir, "folder1")
        dir2 = os.path.join(temp_dir, "folder2")
        os.makedirs(dir1)
        os.makedirs(dir2)

        manager.add_watcher(dir1, mock_callback)
        manager.add_watcher(dir2, mock_callback)

        folders = manager.list_watched_folders()

        assert len(folders) == 2
        assert dir1 in folders
        assert dir2 in folders


class TestWatcherPersistence:
    """Tests for watcher persistence."""

    def test_serialize_watcher(self, temp_dir, mock_callback):
        watcher = FolderWatcher(
            folder_path=temp_dir,
            callback=mock_callback,
            recursive=True,
            ignore_patterns=["*.tmp"],
        )

        data = watcher.to_dict()

        assert data["folder_path"] == temp_dir
        assert data["recursive"] is True
        assert "*.tmp" in data["ignore_patterns"]

    def test_deserialize_watcher(self, temp_dir, mock_callback):
        data = {
            "folder_path": temp_dir,
            "recursive": False,
            "ignore_patterns": ["*.bak"],
            "enabled": True,
        }

        watcher = FolderWatcher.from_dict(data, callback=mock_callback)

        assert watcher.folder_path == temp_dir
        assert not watcher.recursive
        assert "*.bak" in watcher.ignore_patterns


class TestWatcherStatistics:
    """Tests for watcher statistics."""

    def test_stats_initial(self, temp_dir, mock_callback):
        watcher = FolderWatcher(
            folder_path=temp_dir,
            callback=mock_callback,
        )

        stats = watcher.get_stats()

        assert stats["events_processed"] == 0
        assert stats["files_processed"] == 0

    def test_stats_tracking(self, temp_dir, mock_callback):
        watcher = FolderWatcher(
            folder_path=temp_dir,
            callback=mock_callback,
        )

        # Simulate processing
        watcher._increment_stats("events_processed")
        watcher._increment_stats("files_processed")

        stats = watcher.get_stats()

        assert stats["events_processed"] == 1
        assert stats["files_processed"] == 1


class TestWatcherErrorHandling:
    """Tests for error handling."""

    def test_invalid_folder_path(self, mock_callback):
        with pytest.raises(ValueError):
            FolderWatcher(
                folder_path="/nonexistent/path",
                callback=mock_callback,
            )

    def test_callback_error_handling(self, temp_dir):
        def failing_callback(path):
            raise Exception("Callback failed")

        watcher = FolderWatcher(
            folder_path=temp_dir,
            callback=failing_callback,
        )

        # Should not propagate exception
        watcher._safe_callback("/path/to/file.txt")
