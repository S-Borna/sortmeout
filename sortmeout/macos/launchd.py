"""
macOS Launch at Login support via LaunchAgent.

Installs/uninstalls a LaunchAgent plist so SortMeOut starts
automatically when the user logs in.
"""

from __future__ import annotations

import os
import plistlib
import subprocess
import sys
from pathlib import Path
from typing import Optional

from sortmeout.utils.logger import get_logger

logger = get_logger(__name__)

BUNDLE_ID = "com.saidborna.sortmeout"
LAUNCH_AGENTS_DIR = os.path.expanduser("~/Library/LaunchAgents")
PLIST_PATH = os.path.join(LAUNCH_AGENTS_DIR, f"{BUNDLE_ID}.plist")


def _get_executable() -> str:
    """
    Determine the correct executable path.

    If running from a .app bundle, use the binary inside the bundle.
    Otherwise, use the current Python interpreter with the CLI module.
    """
    # Check if we're inside a .app bundle
    exe = sys.executable
    if ".app/Contents/MacOS/" in exe:
        return exe

    # Fallback: run via Python
    return exe


def _get_program_arguments() -> list:
    """Build the ProgramArguments for the plist."""
    exe = _get_executable()

    # If running from a .app bundle
    if ".app/Contents/MacOS/" in exe:
        return [exe, "--background"]

    # Running from source / pip install
    # Try to find the sortmeout CLI entry point
    import shutil

    sortmeout_bin = shutil.which("sortmeout")
    if sortmeout_bin:
        return [sortmeout_bin, "start", "--foreground"]

    # Fallback: python -m sortmeout.cli
    return [exe, "-m", "sortmeout.cli", "start", "--foreground"]


def is_launch_at_login_enabled() -> bool:
    """Check if Launch at Login is currently enabled."""
    return os.path.exists(PLIST_PATH)


def enable_launch_at_login() -> bool:
    """
    Install the LaunchAgent plist to start SortMeOut at login.

    Returns:
        True if successful.
    """
    try:
        os.makedirs(LAUNCH_AGENTS_DIR, exist_ok=True)

        plist = {
            "Label": BUNDLE_ID,
            "ProgramArguments": _get_program_arguments(),
            "RunAtLoad": True,
            "KeepAlive": {
                "SuccessfulExit": False,  # Restart only if it crashes
            },
            "StandardOutPath": os.path.expanduser("~/.sortmeout/launchd-stdout.log"),
            "StandardErrorPath": os.path.expanduser("~/.sortmeout/launchd-stderr.log"),
            "ProcessType": "Background",
        }

        with open(PLIST_PATH, "wb") as f:
            plistlib.dump(plist, f)

        # Load the agent immediately
        subprocess.run(
            ["launchctl", "load", PLIST_PATH],
            capture_output=True,
        )

        logger.info("Launch at Login enabled: %s", PLIST_PATH)
        return True

    except Exception as e:
        logger.error("Failed to enable Launch at Login: %s", e)
        return False


def disable_launch_at_login() -> bool:
    """
    Uninstall the LaunchAgent plist.

    Returns:
        True if successful.
    """
    try:
        if os.path.exists(PLIST_PATH):
            # Unload the agent first
            subprocess.run(
                ["launchctl", "unload", PLIST_PATH],
                capture_output=True,
            )
            os.remove(PLIST_PATH)

        logger.info("Launch at Login disabled")
        return True

    except Exception as e:
        logger.error("Failed to disable Launch at Login: %s", e)
        return False


def set_launch_at_login(enabled: bool) -> bool:
    """
    Enable or disable Launch at Login.

    Args:
        enabled: True to enable, False to disable.

    Returns:
        True if successful.
    """
    if enabled:
        return enable_launch_at_login()
    else:
        return disable_launch_at_login()
