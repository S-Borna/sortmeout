"""
Application settings.

User-configurable settings for SortMeOut behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TrashSettings:
    """Settings for trash management."""
    enabled: bool = False
    max_age_days: int = 30
    max_size_gb: float = 10.0
    app_sweep_enabled: bool = True
    app_sweep_prompt: bool = True  # Ask before cleaning app files

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "max_age_days": self.max_age_days,
            "max_size_gb": self.max_size_gb,
            "app_sweep_enabled": self.app_sweep_enabled,
            "app_sweep_prompt": self.app_sweep_prompt,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TrashSettings":
        return cls(
            enabled=data.get("enabled", False),
            max_age_days=data.get("max_age_days", 30),
            max_size_gb=data.get("max_size_gb", 10.0),
            app_sweep_enabled=data.get("app_sweep_enabled", True),
            app_sweep_prompt=data.get("app_sweep_prompt", True),
        )


@dataclass
class NotificationSettings:
    """Settings for notifications."""
    enabled: bool = True
    show_rule_matches: bool = False
    show_errors: bool = True
    show_summary: bool = True
    summary_interval_minutes: int = 60
    sound_enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "show_rule_matches": self.show_rule_matches,
            "show_errors": self.show_errors,
            "show_summary": self.show_summary,
            "summary_interval_minutes": self.summary_interval_minutes,
            "sound_enabled": self.sound_enabled,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NotificationSettings":
        return cls(
            enabled=data.get("enabled", True),
            show_rule_matches=data.get("show_rule_matches", False),
            show_errors=data.get("show_errors", True),
            show_summary=data.get("show_summary", True),
            summary_interval_minutes=data.get("summary_interval_minutes", 60),
            sound_enabled=data.get("sound_enabled", True),
        )


@dataclass
class LoggingSettings:
    """Settings for logging."""
    level: str = "INFO"
    file_logging: bool = True
    max_log_size_mb: int = 10
    backup_count: int = 5
    action_logging: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level,
            "file_logging": self.file_logging,
            "max_log_size_mb": self.max_log_size_mb,
            "backup_count": self.backup_count,
            "action_logging": self.action_logging,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LoggingSettings":
        return cls(
            level=data.get("level", "INFO"),
            file_logging=data.get("file_logging", True),
            max_log_size_mb=data.get("max_log_size_mb", 10),
            backup_count=data.get("backup_count", 5),
            action_logging=data.get("action_logging", True),
        )


@dataclass
class WatcherSettings:
    """Settings for file watching."""
    latency_seconds: float = 0.5
    debounce_seconds: float = 0.5
    ignore_hidden_files: bool = True
    ignore_system_files: bool = True
    custom_ignore_patterns: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "latency_seconds": self.latency_seconds,
            "debounce_seconds": self.debounce_seconds,
            "ignore_hidden_files": self.ignore_hidden_files,
            "ignore_system_files": self.ignore_system_files,
            "custom_ignore_patterns": self.custom_ignore_patterns,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WatcherSettings":
        return cls(
            latency_seconds=data.get("latency_seconds", 0.5),
            debounce_seconds=data.get("debounce_seconds", 0.5),
            ignore_hidden_files=data.get("ignore_hidden_files", True),
            ignore_system_files=data.get("ignore_system_files", True),
            custom_ignore_patterns=data.get("custom_ignore_patterns", []),
        )


@dataclass
class Settings:
    """
    Main application settings.

    Contains all user-configurable settings for SortMeOut.
    """
    # General
    start_at_login: bool = False
    show_menu_bar_icon: bool = True
    preview_mode: bool = False
    confirm_destructive_actions: bool = True

    # Subsystems
    trash: TrashSettings = field(default_factory=TrashSettings)
    notifications: NotificationSettings = field(default_factory=NotificationSettings)
    logging: LoggingSettings = field(default_factory=LoggingSettings)
    watcher: WatcherSettings = field(default_factory=WatcherSettings)

    # UI preferences
    theme: str = "system"  # system, light, dark
    language: str = "en"
    show_preview_on_hover: bool = True

    # Advanced
    max_concurrent_actions: int = 5
    action_timeout_seconds: int = 300
    retry_failed_actions: bool = False
    retry_count: int = 3

    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary."""
        return {
            "start_at_login": self.start_at_login,
            "show_menu_bar_icon": self.show_menu_bar_icon,
            "preview_mode": self.preview_mode,
            "confirm_destructive_actions": self.confirm_destructive_actions,
            "trash": self.trash.to_dict(),
            "notifications": self.notifications.to_dict(),
            "logging": self.logging.to_dict(),
            "watcher": self.watcher.to_dict(),
            "theme": self.theme,
            "language": self.language,
            "show_preview_on_hover": self.show_preview_on_hover,
            "max_concurrent_actions": self.max_concurrent_actions,
            "action_timeout_seconds": self.action_timeout_seconds,
            "retry_failed_actions": self.retry_failed_actions,
            "retry_count": self.retry_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Settings":
        """Create settings from dictionary."""
        return cls(
            start_at_login=data.get("start_at_login", False),
            show_menu_bar_icon=data.get("show_menu_bar_icon", True),
            preview_mode=data.get("preview_mode", False),
            confirm_destructive_actions=data.get("confirm_destructive_actions", True),
            trash=TrashSettings.from_dict(data.get("trash", {})),
            notifications=NotificationSettings.from_dict(data.get("notifications", {})),
            logging=LoggingSettings.from_dict(data.get("logging", {})),
            watcher=WatcherSettings.from_dict(data.get("watcher", {})),
            theme=data.get("theme", "system"),
            language=data.get("language", "en"),
            show_preview_on_hover=data.get("show_preview_on_hover", True),
            max_concurrent_actions=data.get("max_concurrent_actions", 5),
            action_timeout_seconds=data.get("action_timeout_seconds", 300),
            retry_failed_actions=data.get("retry_failed_actions", False),
            retry_count=data.get("retry_count", 3),
        )
