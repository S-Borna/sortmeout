"""
Main SortMeOut application class.

This module provides the main entry point for the SortMeOut application,
managing folder watches, rules, and the overall lifecycle of the app.
"""

from __future__ import annotations

import logging
import os
import signal
import sys
import threading
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime

from sortmeout.core.watcher import FolderWatcher, WatcherManager
from sortmeout.core.rule import Rule
from sortmeout.core.engine import RuleEngine
from sortmeout.config.manager import ConfigManager
from sortmeout.config.settings import Settings
from sortmeout.utils.logger import setup_logging, get_logger

logger = get_logger(__name__)


class SortMeOut:
    """
    Main application class for SortMeOut file automation.

    This class manages:
    - Folder watchers for monitoring file system changes
    - Rules and their associations with folders
    - Configuration persistence
    - Application lifecycle

    Example:
        >>> app = SortMeOut()
        >>> app.add_folder("~/Downloads")
        >>> rule = Rule(name="PDF Organizer", ...)
        >>> app.add_rule("~/Downloads", rule)
        >>> app.start()
    """

    def __init__(
        self,
        config_path: Optional[str] = None,
        preview_mode: bool = False,
        verbose: bool = False,
    ):
        """
        Initialize SortMeOut application.

        Args:
            config_path: Path to configuration file. If None, uses default location.
            preview_mode: If True, rules are evaluated but actions are not executed.
            verbose: Enable verbose logging.
        """
        self._preview_mode = preview_mode
        self._verbose = verbose
        self._running = False
        self._lock = threading.RLock()

        # Set up logging
        log_level = logging.DEBUG if verbose else logging.INFO
        setup_logging(level=log_level)

        # Initialize components
        self._config_manager = ConfigManager(config_path)
        self._settings = self._config_manager.load_settings()
        self._watcher_manager = WatcherManager()
        self._rule_engine = RuleEngine(preview_mode=preview_mode)

        # Folder -> Rules mapping
        self._folder_rules: Dict[str, List[Rule]] = {}

        # Event callbacks
        self._callbacks: Dict[str, List[Callable[..., Any]]] = {
            "rule_matched": [],
            "action_executed": [],
            "error": [],
            "file_processed": [],
        }

        # Statistics
        self._stats = {
            "files_processed": 0,
            "rules_matched": 0,
            "actions_executed": 0,
            "errors": 0,
            "start_time": None,
        }

        # Load saved configuration
        self._load_saved_config()

        logger.info("SortMeOut initialized (preview_mode=%s)", preview_mode)

    def _load_saved_config(self) -> None:
        """Load folders and rules from saved configuration."""
        config = self._config_manager.load_config()

        for folder_config in config.get("folders", []):
            folder_path = folder_config["path"]
            self._folder_rules[folder_path] = []

            for rule_dict in folder_config.get("rules", []):
                rule = Rule.from_dict(rule_dict)
                self._folder_rules[folder_path].append(rule)

            logger.debug("Loaded folder: %s with %d rules",
                        folder_path, len(self._folder_rules[folder_path]))

    def add_folder(
        self,
        path: str,
        recursive: bool = False,
        enabled: bool = True,
    ) -> bool:
        """
        Add a folder to watch for file changes.

        Args:
            path: Path to the folder to watch.
            recursive: Watch subdirectories as well.
            enabled: Whether watching is enabled.

        Returns:
            True if folder was added successfully.

        Raises:
            ValueError: If path is not a valid directory.
        """
        # Expand user path
        expanded_path = os.path.expanduser(path)
        resolved_path = str(Path(expanded_path).resolve())

        if not os.path.isdir(resolved_path):
            raise ValueError(f"Path is not a valid directory: {path}")

        with self._lock:
            if resolved_path in self._folder_rules:
                logger.warning("Folder already being watched: %s", resolved_path)
                return False

            self._folder_rules[resolved_path] = []

            if self._running and enabled:
                self._watcher_manager.add_watch(
                    resolved_path,
                    callback=self._on_file_event,
                    recursive=recursive,
                )

            logger.info("Added folder: %s (recursive=%s)", resolved_path, recursive)
            self._save_config()
            return True

    def remove_folder(self, path: str) -> bool:
        """
        Remove a folder from watching.

        Args:
            path: Path to the folder to remove.

        Returns:
            True if folder was removed successfully.
        """
        expanded_path = os.path.expanduser(path)
        resolved_path = str(Path(expanded_path).resolve())

        with self._lock:
            if resolved_path not in self._folder_rules:
                logger.warning("Folder not found: %s", resolved_path)
                return False

            del self._folder_rules[resolved_path]

            if self._running:
                self._watcher_manager.remove_watch(resolved_path)

            logger.info("Removed folder: %s", resolved_path)
            self._save_config()
            return True

    def get_folders(self) -> List[str]:
        """Get list of all watched folders."""
        with self._lock:
            return list(self._folder_rules.keys())

    def add_rule(self, folder_path: str, rule: Rule) -> bool:
        """
        Add a rule to a watched folder.

        Args:
            folder_path: Path to the folder.
            rule: Rule to add.

        Returns:
            True if rule was added successfully.
        """
        expanded_path = os.path.expanduser(folder_path)
        resolved_path = str(Path(expanded_path).resolve())

        with self._lock:
            if resolved_path not in self._folder_rules:
                raise ValueError(f"Folder not being watched: {folder_path}")

            # Check for duplicate rule names
            existing_names = {r.name for r in self._folder_rules[resolved_path]}
            if rule.name in existing_names:
                logger.warning("Rule with name '%s' already exists", rule.name)
                return False

            self._folder_rules[resolved_path].append(rule)
            logger.info("Added rule '%s' to folder: %s", rule.name, resolved_path)
            self._save_config()
            return True

    def remove_rule(self, folder_path: str, rule_name: str) -> bool:
        """
        Remove a rule from a folder.

        Args:
            folder_path: Path to the folder.
            rule_name: Name of the rule to remove.

        Returns:
            True if rule was removed successfully.
        """
        expanded_path = os.path.expanduser(folder_path)
        resolved_path = str(Path(expanded_path).resolve())

        with self._lock:
            if resolved_path not in self._folder_rules:
                return False

            rules = self._folder_rules[resolved_path]
            for i, rule in enumerate(rules):
                if rule.name == rule_name:
                    del rules[i]
                    logger.info("Removed rule '%s' from folder: %s", rule_name, resolved_path)
                    self._save_config()
                    return True

            return False

    def get_rules(self, folder_path: str) -> List[Rule]:
        """
        Get all rules for a folder.

        Args:
            folder_path: Path to the folder.

        Returns:
            List of rules for the folder.
        """
        expanded_path = os.path.expanduser(folder_path)
        resolved_path = str(Path(expanded_path).resolve())

        with self._lock:
            return list(self._folder_rules.get(resolved_path, []))

    def update_rule(self, folder_path: str, rule_name: str, updated_rule: Rule) -> bool:
        """
        Update an existing rule.

        Args:
            folder_path: Path to the folder.
            rule_name: Name of the rule to update.
            updated_rule: The updated rule.

        Returns:
            True if rule was updated successfully.
        """
        expanded_path = os.path.expanduser(folder_path)
        resolved_path = str(Path(expanded_path).resolve())

        with self._lock:
            if resolved_path not in self._folder_rules:
                return False

            rules = self._folder_rules[resolved_path]
            for i, rule in enumerate(rules):
                if rule.name == rule_name:
                    rules[i] = updated_rule
                    logger.info("Updated rule '%s' in folder: %s", rule_name, resolved_path)
                    self._save_config()
                    return True

            return False

    def reorder_rules(self, folder_path: str, rule_names: List[str]) -> bool:
        """
        Reorder rules for a folder.

        Args:
            folder_path: Path to the folder.
            rule_names: List of rule names in desired order.

        Returns:
            True if rules were reordered successfully.
        """
        expanded_path = os.path.expanduser(folder_path)
        resolved_path = str(Path(expanded_path).resolve())

        with self._lock:
            if resolved_path not in self._folder_rules:
                return False

            rules = self._folder_rules[resolved_path]
            rule_map = {r.name: r for r in rules}

            if set(rule_names) != set(rule_map.keys()):
                logger.error("Rule names don't match existing rules")
                return False

            self._folder_rules[resolved_path] = [rule_map[name] for name in rule_names]
            logger.info("Reordered rules in folder: %s", resolved_path)
            self._save_config()
            return True

    def _on_file_event(self, event_type: str, file_path: str, folder_path: str) -> None:
        """
        Handle file system events.

        Args:
            event_type: Type of event (created, modified, moved, deleted).
            file_path: Path to the affected file.
            folder_path: Path to the watched folder.
        """
        # Skip certain files
        if self._should_skip_file(file_path):
            return

        logger.debug("File event: %s - %s", event_type, file_path)

        # Process file with rules
        if event_type in ("created", "modified"):
            self._process_file(file_path, folder_path)

    def _should_skip_file(self, file_path: str) -> bool:
        """Check if a file should be skipped from processing."""
        path = Path(file_path)

        # Skip hidden files (starting with .)
        if path.name.startswith("."):
            return True

        # Skip temporary files
        temp_extensions = {".tmp", ".temp", ".part", ".crdownload", ".download"}
        if path.suffix.lower() in temp_extensions:
            return True

        # Skip directories
        if path.is_dir():
            return True

        return False

    def _process_file(self, file_path: str, folder_path: str) -> None:
        """
        Process a file against all rules for its folder.

        Args:
            file_path: Path to the file to process.
            folder_path: Path to the watched folder.
        """
        with self._lock:
            rules = self._folder_rules.get(folder_path, [])

        if not rules:
            return

        # Process through rule engine
        result = self._rule_engine.process_file(file_path, rules)

        # Update statistics
        self._stats["files_processed"] += 1
        if result.matched_rules:
            self._stats["rules_matched"] += len(result.matched_rules)
        if result.executed_actions:
            self._stats["actions_executed"] += len(result.executed_actions)
        if result.errors:
            self._stats["errors"] += len(result.errors)

        # Fire callbacks
        for rule_name in result.matched_rules:
            self._fire_callback("rule_matched", file_path, rule_name)

        for action_result in result.executed_actions:
            self._fire_callback("action_executed", file_path, action_result)

        for error in result.errors:
            self._fire_callback("error", file_path, error)

        self._fire_callback("file_processed", file_path, result)

    def process_folder(self, folder_path: str, force: bool = False) -> Dict[str, Any]:
        """
        Process all existing files in a folder.

        Args:
            folder_path: Path to the folder to process.
            force: Process files even if already processed.

        Returns:
            Dictionary with processing results.
        """
        expanded_path = os.path.expanduser(folder_path)
        resolved_path = str(Path(expanded_path).resolve())

        if resolved_path not in self._folder_rules:
            raise ValueError(f"Folder not being watched: {folder_path}")

        results = {
            "processed": 0,
            "matched": 0,
            "errors": 0,
            "files": [],
        }

        for entry in os.scandir(resolved_path):
            if entry.is_file() and not self._should_skip_file(entry.path):
                self._process_file(entry.path, resolved_path)
                results["processed"] += 1
                results["files"].append(entry.path)

        logger.info("Processed %d files in folder: %s", results["processed"], resolved_path)
        return results

    def on(self, event: str, callback: Callable[..., Any]) -> None:
        """
        Register a callback for an event.

        Args:
            event: Event name (rule_matched, action_executed, error, file_processed).
            callback: Callback function.
        """
        if event not in self._callbacks:
            raise ValueError(f"Unknown event: {event}")

        self._callbacks[event].append(callback)

    def off(self, event: str, callback: Callable[..., Any]) -> None:
        """
        Unregister a callback for an event.

        Args:
            event: Event name.
            callback: Callback function to remove.
        """
        if event in self._callbacks and callback in self._callbacks[event]:
            self._callbacks[event].remove(callback)

    def _fire_callback(self, event: str, *args: Any) -> None:
        """Fire all callbacks for an event."""
        for callback in self._callbacks.get(event, []):
            try:
                callback(*args)
            except Exception as e:
                logger.error("Callback error for event '%s': %s", event, e)

    def _save_config(self) -> None:
        """Save current configuration to file."""
        config = {
            "folders": [
                {
                    "path": folder_path,
                    "rules": [rule.to_dict() for rule in rules],
                }
                for folder_path, rules in self._folder_rules.items()
            ]
        }
        self._config_manager.save_config(config)

    def start(self) -> None:
        """
        Start watching all folders.

        This method starts the file system watchers for all configured folders.
        It blocks until stop() is called or a signal is received.
        """
        if self._running:
            logger.warning("Already running")
            return

        self._running = True
        self._stats["start_time"] = datetime.now()

        # Set up signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        # Start watchers for all folders
        for folder_path in self._folder_rules:
            self._watcher_manager.add_watch(
                folder_path,
                callback=self._on_file_event,
                recursive=False,
            )

        logger.info("SortMeOut started, watching %d folders", len(self._folder_rules))

        # Start the watcher manager
        self._watcher_manager.start()

    def start_background(self) -> threading.Thread:
        """
        Start watching in a background thread.

        Returns:
            The background thread.
        """
        thread = threading.Thread(target=self.start, daemon=True)
        thread.start()
        return thread

    def stop(self) -> None:
        """Stop watching all folders."""
        if not self._running:
            return

        self._running = False
        self._watcher_manager.stop()

        logger.info("SortMeOut stopped")

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """Handle shutdown signals."""
        logger.info("Received signal %d, shutting down...", signum)
        self.stop()
        sys.exit(0)

    def get_stats(self) -> Dict[str, Any]:
        """Get current statistics."""
        stats = self._stats.copy()
        if stats["start_time"]:
            stats["uptime"] = str(datetime.now() - stats["start_time"])
        return stats

    @property
    def is_running(self) -> bool:
        """Check if the application is running."""
        return self._running

    @property
    def preview_mode(self) -> bool:
        """Check if preview mode is enabled."""
        return self._preview_mode

    @preview_mode.setter
    def preview_mode(self, value: bool) -> None:
        """Set preview mode."""
        self._preview_mode = value
        self._rule_engine.preview_mode = value

    def export_rules(self, folder_path: str, output_path: str) -> bool:
        """
        Export rules for a folder to a file.

        Args:
            folder_path: Path to the folder.
            output_path: Path to export to.

        Returns:
            True if export was successful.
        """
        import json

        rules = self.get_rules(folder_path)
        if not rules:
            return False

        export_data = {
            "version": "1.0",
            "folder": folder_path,
            "rules": [rule.to_dict() for rule in rules],
        }

        with open(output_path, "w") as f:
            json.dump(export_data, f, indent=2)

        logger.info("Exported %d rules to: %s", len(rules), output_path)
        return True

    def import_rules(self, folder_path: str, input_path: str) -> int:
        """
        Import rules from a file to a folder.

        Args:
            folder_path: Path to the folder.
            input_path: Path to import from.

        Returns:
            Number of rules imported.
        """
        import json

        expanded_path = os.path.expanduser(folder_path)
        resolved_path = str(Path(expanded_path).resolve())

        if resolved_path not in self._folder_rules:
            raise ValueError(f"Folder not being watched: {folder_path}")

        with open(input_path, "r") as f:
            import_data = json.load(f)

        imported = 0
        for rule_dict in import_data.get("rules", []):
            rule = Rule.from_dict(rule_dict)
            if self.add_rule(folder_path, rule):
                imported += 1

        logger.info("Imported %d rules from: %s", imported, input_path)
        return imported
