"""
Configuration file management.

Handles reading and writing configuration files for SortMeOut.
"""

from __future__ import annotations

import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
import appdirs

from sortmeout.config.settings import Settings
from sortmeout.utils.logger import get_logger

logger = get_logger(__name__)

# Application identifiers
APP_NAME = "SortMeOut"
APP_AUTHOR = "SortMeOut"


def get_config_directory() -> Path:
    """Get the configuration directory path."""
    config_dir = Path(appdirs.user_config_dir(APP_NAME, APP_AUTHOR))
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_data_directory() -> Path:
    """Get the data directory path."""
    data_dir = Path(appdirs.user_data_dir(APP_NAME, APP_AUTHOR))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


class ConfigManager:
    """
    Manages configuration file operations.

    Handles loading, saving, and migrating configuration files.
    Supports both YAML and JSON formats.
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration manager.

        Args:
            config_path: Path to configuration file. If None, uses default.
        """
        if config_path:
            self.config_path = Path(config_path)
        else:
            config_dir = get_config_directory()
            yaml_path = config_dir / "config.yaml"
            json_path = config_dir / "config.json"
            # Prefer YAML; fall back to existing JSON for backward-compat
            if yaml_path.exists():
                self.config_path = yaml_path
            elif json_path.exists():
                self.config_path = json_path
            else:
                self.config_path = yaml_path  # new installs default to YAML

        self.config_dir = self.config_path.parent
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Backup directory
        self.backup_dir = self.config_dir / "backups"
        self.backup_dir.mkdir(exist_ok=True)

        logger.debug("Config path: %s", self.config_path)

    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from file.

        Returns:
            Configuration dictionary.
        """
        if not self.config_path.exists():
            logger.info("No config file found, using defaults")
            return self._get_default_config()

        try:
            with open(self.config_path, "r") as f:
                if self.config_path.suffix in (".yaml", ".yml"):
                    config = yaml.safe_load(f) or {}
                else:
                    config = json.load(f)

            logger.info("Loaded config from: %s", self.config_path)
            return config

        except Exception as e:
            logger.error("Failed to load config: %s", e)
            return self._get_default_config()

    def save_config(self, config: Dict[str, Any]) -> bool:
        """
        Save configuration to file.

        Args:
            config: Configuration dictionary to save.

        Returns:
            True if save was successful.
        """
        try:
            # Create backup before saving
            if self.config_path.exists():
                self._create_backup()

            # Add metadata
            config["_metadata"] = {
                "version": "1.0",
                "updated_at": datetime.now().isoformat(),
                "app_version": "0.1.0",
            }

            with open(self.config_path, "w") as f:
                if self.config_path.suffix in (".yaml", ".yml"):
                    yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)
                else:
                    json.dump(config, f, indent=2)

            logger.info("Saved config to: %s", self.config_path)
            return True

        except Exception as e:
            logger.error("Failed to save config: %s", e)
            return False

    def load_settings(self) -> Settings:
        """
        Load application settings.

        Returns:
            Settings object.
        """
        settings_path = self.config_dir / "settings.yaml"

        if settings_path.exists():
            try:
                with open(settings_path, "r") as f:
                    data = yaml.safe_load(f) or {}
                return Settings.from_dict(data)
            except Exception as e:
                logger.error("Failed to load settings: %s", e)

        return Settings()

    def save_settings(self, settings: Settings) -> bool:
        """
        Save application settings.

        Args:
            settings: Settings object to save.

        Returns:
            True if save was successful.
        """
        settings_path = self.config_dir / "settings.yaml"

        try:
            with open(settings_path, "w") as f:
                yaml.safe_dump(settings.to_dict(), f, default_flow_style=False)
            return True
        except Exception as e:
            logger.error("Failed to save settings: %s", e)
            return False

    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration."""
        return {
            "folders": [],
            "_metadata": {
                "version": "1.0",
                "created_at": datetime.now().isoformat(),
                "app_version": "0.1.0",
            },
        }

    def _create_backup(self) -> None:
        """Create a backup of the current config file."""
        if not self.config_path.exists():
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"config_backup_{timestamp}{self.config_path.suffix}"
        backup_path = self.backup_dir / backup_name

        shutil.copy2(self.config_path, backup_path)
        logger.debug("Created config backup: %s", backup_path)

        # Keep only last 10 backups
        self._cleanup_old_backups()

    def _cleanup_old_backups(self, keep: int = 10) -> None:
        """Remove old backup files."""
        backups = sorted(self.backup_dir.glob("config_backup_*"))

        if len(backups) > keep:
            for backup in backups[:-keep]:
                backup.unlink()
                logger.debug("Removed old backup: %s", backup)

    def restore_backup(self, backup_name: Optional[str] = None) -> bool:
        """
        Restore configuration from a backup.

        Args:
            backup_name: Name of backup file. If None, uses most recent.

        Returns:
            True if restore was successful.
        """
        if backup_name:
            backup_path = self.backup_dir / backup_name
        else:
            backups = sorted(self.backup_dir.glob("config_backup_*"))
            if not backups:
                logger.warning("No backups found")
                return False
            backup_path = backups[-1]

        if not backup_path.exists():
            logger.error("Backup not found: %s", backup_path)
            return False

        try:
            shutil.copy2(backup_path, self.config_path)
            logger.info("Restored config from: %s", backup_path)
            return True
        except Exception as e:
            logger.error("Failed to restore backup: %s", e)
            return False

    def list_backups(self) -> list:
        """List available backup files."""
        return sorted([b.name for b in self.backup_dir.glob("config_backup_*")])

    def export_config(self, output_path: str, format: str = "yaml") -> bool:
        """
        Export configuration to a file.

        Args:
            output_path: Path to export to.
            format: Export format (yaml or json).

        Returns:
            True if export was successful.
        """
        config = self.load_config()

        try:
            with open(output_path, "w") as f:
                if format == "yaml":
                    yaml.safe_dump(config, f, default_flow_style=False)
                else:
                    json.dump(config, f, indent=2)

            logger.info("Exported config to: %s", output_path)
            return True

        except Exception as e:
            logger.error("Failed to export config: %s", e)
            return False

    def import_config(self, input_path: str, merge: bool = False) -> bool:
        """
        Import configuration from a file.

        Args:
            input_path: Path to import from.
            merge: Merge with existing config instead of replacing.

        Returns:
            True if import was successful.
        """
        try:
            with open(input_path, "r") as f:
                if input_path.endswith((".yaml", ".yml")):
                    imported = yaml.safe_load(f) or {}
                else:
                    imported = json.load(f)

            if merge:
                current = self.load_config()
                # Merge folders
                current_folders = {f["path"]: f for f in current.get("folders", [])}
                for folder in imported.get("folders", []):
                    current_folders[folder["path"]] = folder
                current["folders"] = list(current_folders.values())
                config = current
            else:
                config = imported

            return self.save_config(config)

        except Exception as e:
            logger.error("Failed to import config: %s", e)
            return False

    def reset_config(self) -> bool:
        """
        Reset configuration to defaults.

        Creates a backup before resetting.

        Returns:
            True if reset was successful.
        """
        self._create_backup()
        return self.save_config(self._get_default_config())
