"""
macOS Menu Bar application for SortMeOut.

Provides a menu bar interface for controlling SortMeOut.
"""

from __future__ import annotations

import os
import sys
import threading
import webbrowser
from typing import Optional

try:
    import rumps
except ImportError:
    rumps = None

from sortmeout import SortMeOut, __version__
from sortmeout.config.manager import ConfigManager
from sortmeout.macos.trash import get_trash_info, empty_trash
from sortmeout.utils.logger import setup_logging, get_logger

logger = get_logger(__name__)


class MenuBarApp:
    """
    Menu bar application for SortMeOut.

    Provides quick access to:
    - Start/stop watching
    - View status
    - Access settings
    - View recent activity
    """

    def __init__(self):
        """Initialize the menu bar app."""
        if rumps is None:
            raise ImportError("rumps is required for the GUI. Install with: pip install rumps")

        self.app = rumps.App(
            "SortMeOut",
            icon=self._get_icon_path(),
            quit_button=None,  # We'll add our own
        )

        # Initialize SortMeOut
        self.sortmeout = SortMeOut()
        self._running = False
        self._preview_mode = False

        # Build menu
        self._build_menu()

        # Set up timer for status updates
        self._status_timer = rumps.Timer(self._update_status, 30)
        self._status_timer.start()

    def _get_icon_path(self) -> Optional[str]:
        """Get path to menu bar icon."""
        # Try to find icon in resources
        resource_paths = [
            os.path.join(os.path.dirname(__file__), "..", "resources", "icon.png"),
            os.path.join(os.path.dirname(__file__), "..", "resources", "MenuBarIcon.png"),
        ]

        for path in resource_paths:
            if os.path.exists(path):
                return path

        return None

    def _build_menu(self) -> None:
        """Build the menu bar menu."""
        self.app.menu = [
            rumps.MenuItem("Start Watching", callback=self._toggle_watching),
            rumps.MenuItem("Preview Mode", callback=self._toggle_preview),
            None,  # Separator
            rumps.MenuItem("Folders", callback=None),
            rumps.MenuItem("Recent Activity", callback=self._show_activity),
            None,
            rumps.MenuItem("Trash", [
                rumps.MenuItem("View Trash Status", callback=self._show_trash_status),
                rumps.MenuItem("Empty Trash", callback=self._empty_trash),
            ]),
            None,
            rumps.MenuItem("Preferences...", callback=self._show_preferences),
            rumps.MenuItem("Help", [
                rumps.MenuItem("Documentation", callback=self._open_docs),
                rumps.MenuItem("Report Issue", callback=self._report_issue),
                rumps.MenuItem(f"About SortMeOut v{__version__}", callback=self._show_about),
            ]),
            None,
            rumps.MenuItem("Quit SortMeOut", callback=self._quit),
        ]

        # Update folders submenu
        self._update_folders_menu()

    def _update_folders_menu(self) -> None:
        """Update the folders submenu."""
        folders_menu = self.app.menu["Folders"]

        # Clear existing items
        folders_menu.clear()

        folders = self.sortmeout.get_folders()

        if not folders:
            folders_menu.add(rumps.MenuItem("No folders configured", callback=None))
            folders_menu["No folders configured"].set_callback(None)
        else:
            for folder in folders:
                rules = self.sortmeout.get_rules(folder)
                folder_name = os.path.basename(folder) or folder
                item = rumps.MenuItem(
                    f"{folder_name} ({len(rules)} rules)",
                    callback=lambda _, f=folder: self._show_folder_details(f)
                )
                folders_menu.add(item)

        # Add separator and "Add Folder" option
        folders_menu.add(None)
        folders_menu.add(rumps.MenuItem("Add Folder...", callback=self._add_folder))

    def _toggle_watching(self, sender: rumps.MenuItem) -> None:
        """Toggle watching on/off."""
        if self._running:
            self.sortmeout.stop()
            self._running = False
            sender.title = "Start Watching"
            self.app.title = "SortMeOut"
            rumps.notification(
                "SortMeOut",
                "Stopped",
                "File watching has been stopped."
            )
        else:
            self.sortmeout.start_background()
            self._running = True
            sender.title = "Stop Watching"
            self.app.title = "SortMeOut ●"
            rumps.notification(
                "SortMeOut",
                "Started",
                f"Watching {len(self.sortmeout.get_folders())} folder(s)."
            )

    def _toggle_preview(self, sender: rumps.MenuItem) -> None:
        """Toggle preview mode."""
        self._preview_mode = not self._preview_mode
        self.sortmeout.preview_mode = self._preview_mode

        if self._preview_mode:
            sender.state = 1  # Checkmark
            rumps.notification(
                "SortMeOut",
                "Preview Mode",
                "Actions will be logged but not executed."
            )
        else:
            sender.state = 0

    def _show_activity(self, _) -> None:
        """Show recent activity."""
        stats = self.sortmeout.get_stats()

        rumps.alert(
            title="Recent Activity",
            message=(
                f"Files processed: {stats['files_processed']}\n"
                f"Rules matched: {stats['rules_matched']}\n"
                f"Actions executed: {stats['actions_executed']}\n"
                f"Errors: {stats['errors']}"
            )
        )

    def _show_folder_details(self, folder: str) -> None:
        """Show details for a folder."""
        rules = self.sortmeout.get_rules(folder)

        if not rules:
            message = "No rules configured"
        else:
            rule_names = "\n".join(f"• {r.name}" for r in rules)
            message = f"Rules:\n{rule_names}"

        response = rumps.alert(
            title=f"Folder: {os.path.basename(folder)}",
            message=message,
            ok="Close",
            cancel="Process Now"
        )

        if response == 0:  # Cancel = Process Now
            self.sortmeout.process_folder(folder)
            rumps.notification(
                "SortMeOut",
                "Processing Complete",
                f"Processed files in {os.path.basename(folder)}"
            )

    def _add_folder(self, _) -> None:
        """Open dialog to add a folder."""
        try:
            # Use AppleScript to show folder picker
            import subprocess
            script = '''
                tell application "System Events"
                    activate
                    set theFolder to choose folder with prompt "Select a folder to watch:"
                    return POSIX path of theFolder
                end tell
            '''
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0 and result.stdout.strip():
                folder = result.stdout.strip()
                if self.sortmeout.add_folder(folder):
                    self._update_folders_menu()
                    rumps.notification(
                        "SortMeOut",
                        "Folder Added",
                        f"Now watching: {os.path.basename(folder)}"
                    )
        except Exception as e:
            logger.error("Failed to add folder: %s", e)

    def _show_trash_status(self, _) -> None:
        """Show Trash status."""
        info = get_trash_info()

        rumps.alert(
            title="Trash Status",
            message=(
                f"Items: {info.item_count}\n"
                f"Size: {info.size_human}\n"
                f"Oldest item: {info.oldest_item_date.strftime('%Y-%m-%d') if info.oldest_item_date else 'N/A'}"
            )
        )

    def _empty_trash(self, _) -> None:
        """Empty the Trash."""
        response = rumps.alert(
            title="Empty Trash",
            message="Are you sure you want to empty the Trash? This cannot be undone.",
            ok="Empty Trash",
            cancel="Cancel"
        )

        if response == 1:  # OK
            if empty_trash():
                rumps.notification(
                    "SortMeOut",
                    "Trash Emptied",
                    "The Trash has been emptied."
                )

    def _show_preferences(self, _) -> None:
        """Show preferences window."""
        # In a full implementation, this would open a preferences window
        rumps.alert(
            title="Preferences",
            message="Preferences window coming soon!\n\nFor now, use the CLI:\nsortmeout config show"
        )

    def _open_docs(self, _) -> None:
        """Open documentation."""
        webbrowser.open("https://github.com/yourusername/sortmeout/docs")

    def _report_issue(self, _) -> None:
        """Open issue tracker."""
        webbrowser.open("https://github.com/yourusername/sortmeout/issues")

    def _show_about(self, _) -> None:
        """Show about dialog."""
        rumps.alert(
            title="About SortMeOut",
            message=(
                f"SortMeOut v{__version__}\n\n"
                "Open-source file automation for macOS.\n\n"
                "Inspired by Noodlesoft Hazel.\n\n"
                "https://github.com/yourusername/sortmeout"
            )
        )

    def _update_status(self, _) -> None:
        """Periodic status update."""
        if self._running:
            stats = self.sortmeout.get_stats()
            # Could update menu bar icon or title based on activity

    def _quit(self, _) -> None:
        """Quit the application."""
        if self._running:
            self.sortmeout.stop()
        rumps.quit_application()

    def run(self) -> None:
        """Run the menu bar app."""
        self.app.run()


def main():
    """Main entry point for GUI application."""
    setup_logging()

    if rumps is None:
        print("Error: rumps is required for the GUI.")
        print("Install with: pip install rumps")
        sys.exit(1)

    app = MenuBarApp()
    app.run()


if __name__ == "__main__":
    main()
