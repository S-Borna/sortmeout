"""
Logging configuration for SortMeOut.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

import appdirs

# Application name for directories
APP_NAME = "SortMeOut"
APP_AUTHOR = "SortMeOut"

# Default log format
DEFAULT_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
SIMPLE_FORMAT = "%(levelname)s: %(message)s"
DETAILED_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"


def get_log_directory() -> Path:
    """Get the log directory path."""
    log_dir = Path(appdirs.user_log_dir(APP_NAME, APP_AUTHOR))
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    console: bool = True,
    file_logging: bool = True,
    max_file_size: int = 10 * 1024 * 1024,  # 10 MB
    backup_count: int = 5,
    format_string: Optional[str] = None,
) -> logging.Logger:
    """
    Set up logging for the application.

    Args:
        level: Logging level.
        log_file: Path to log file. If None, uses default location.
        console: Enable console logging.
        file_logging: Enable file logging.
        max_file_size: Maximum log file size before rotation.
        backup_count: Number of backup files to keep.
        format_string: Custom format string.

    Returns:
        Root logger instance.
    """
    # Get root logger for our package
    root_logger = logging.getLogger("sortmeout")
    root_logger.setLevel(level)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Determine format
    if format_string is None:
        format_string = DETAILED_FORMAT if level == logging.DEBUG else DEFAULT_FORMAT

    formatter = logging.Formatter(format_string)

    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(logging.Formatter(SIMPLE_FORMAT))
        root_logger.addHandler(console_handler)

    # File handler
    if file_logging:
        if log_file is None:
            log_dir = get_log_directory()
            log_file = str(log_dir / "sortmeout.log")

        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a module.

    Args:
        name: Logger name (usually __name__).

    Returns:
        Logger instance.
    """
    # Ensure name is under our package namespace
    if not name.startswith("sortmeout"):
        name = f"sortmeout.{name}"

    return logging.getLogger(name)


class ActionLogger:
    """
    Specialized logger for tracking file actions.

    Logs actions to a separate file for easy auditing.
    """

    def __init__(self, log_file: Optional[str] = None):
        """
        Initialize action logger.

        Args:
            log_file: Path to action log file.
        """
        self.logger = logging.getLogger("sortmeout.actions")
        self.logger.setLevel(logging.INFO)

        if log_file is None:
            log_dir = get_log_directory()
            log_file = str(log_dir / "actions.log")

        handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=10,
        )
        handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(message)s"
        ))
        self.logger.addHandler(handler)

    def log_action(
        self,
        action_type: str,
        source: str,
        destination: Optional[str] = None,
        success: bool = True,
        details: Optional[str] = None,
    ) -> None:
        """
        Log a file action.

        Args:
            action_type: Type of action performed.
            source: Source file path.
            destination: Destination path (if applicable).
            success: Whether action succeeded.
            details: Additional details.
        """
        status = "SUCCESS" if success else "FAILED"

        message_parts = [
            status,
            action_type.upper(),
            f"src={source}",
        ]

        if destination:
            message_parts.append(f"dst={destination}")

        if details:
            message_parts.append(f"({details})")

        message = " | ".join(message_parts)

        if success:
            self.logger.info(message)
        else:
            self.logger.error(message)

    def get_recent_actions(self, count: int = 100) -> list:
        """
        Get recent logged actions.

        Args:
            count: Number of recent actions to retrieve.

        Returns:
            List of action log entries.
        """
        log_dir = get_log_directory()
        log_file = log_dir / "actions.log"

        if not log_file.exists():
            return []

        with open(log_file, "r") as f:
            lines = f.readlines()

        return lines[-count:]


# Global action logger instance
_action_logger: Optional[ActionLogger] = None


def get_action_logger() -> ActionLogger:
    """Get the global action logger instance."""
    global _action_logger
    if _action_logger is None:
        _action_logger = ActionLogger()
    return _action_logger
