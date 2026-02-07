"""
macOS Menu Bar application for SortMeOut.

Unified menu bar interface — single entry point for all GUI functionality.
Uses rumps for menu bar integration, ConfigManager (YAML) for all config,
and delegates to the core engine for file operations.
"""

from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
import webbrowser
from collections import deque
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
    Unified menu bar application for SortMeOut.

    Provides quick access to:
    - Start/stop watching
    - Preview mode toggle
    - Folder & rule management
    - AI Assistant & file analysis
    - Organize Now (batch)
    - Settings, license, trash management
    - First-run onboarding
    """

    def __init__(self):
        """Initialize the menu bar app."""
        if rumps is None:
            raise ImportError(
                "rumps is required for the GUI. Install with: pip install rumps"
            )

        self.app = rumps.App(
            "SortMeOut",
            icon=self._get_icon_path(),
            quit_button=None,
        )

        # Config — single YAML-based system
        self._config_manager = ConfigManager()
        self._settings = self._config_manager.load_settings()

        # Core coordinator
        self.sortmeout = SortMeOut()
        self._running = False
        self._preview_mode = False

        # Notification batching — collect events, send grouped summaries
        self._notification_queue: deque = deque(maxlen=200)
        self._notification_lock = threading.Lock()

        # License
        from sortmeout.core.license import get_license
        self._license = get_license()

        # Check first-run — use onboarding_completed flag, not file existence
        config_data = self._config_manager.load_config()
        self._first_run = not config_data.get("onboarding_completed", False)

        # Build menu
        self._build_menu()

        # Status update timer
        self._status_timer = rumps.Timer(self._update_status, 30)
        self._status_timer.start()

        # Trigger onboarding after a short delay if first-run
        if self._first_run:
            rumps.Timer(self._run_onboarding, 1).start()

    # ──────────────────────────────────────────────────────────────────
    # ICON
    # ──────────────────────────────────────────────────────────────────

    def _get_icon_path(self) -> Optional[str]:
        """Get path to menu bar icon."""
        resource_paths = [
            os.path.join(os.path.dirname(__file__), "..", "resources", "icon.png"),
            os.path.join(os.path.dirname(__file__), "..", "resources", "MenuBarIcon.png"),
        ]
        for path in resource_paths:
            if os.path.exists(path):
                return path
        return None

    # ──────────────────────────────────────────────────────────────────
    # MENU
    # ──────────────────────────────────────────────────────────────────

    def _build_menu(self) -> None:
        """Build the menu bar menu."""
        status_msg = self._license.get_status_message()

        self.app.menu = [
            rumps.MenuItem(status_msg, callback=None),
            None,
            rumps.MenuItem("💬 AI Assistant...", callback=self._open_ai_assistant),
            rumps.MenuItem("📎 Analyze File...", callback=self._analyze_file),
            None,
            rumps.MenuItem("Start Watching", callback=self._toggle_watching),
            rumps.MenuItem("Preview Mode", callback=self._toggle_preview),
            rumps.MenuItem("Organize Now", callback=self._organize_now),
            None,
            rumps.MenuItem("Folders", callback=None),
            rumps.MenuItem("Recent Activity", callback=self._show_activity),
            None,
            rumps.MenuItem("Quick Add Rule...", callback=self._quick_add_rule),
            rumps.MenuItem("Advanced Rule Editor...", callback=self._advanced_rule_editor),
            None,
            rumps.MenuItem(
                "Trash",
            ),
            None,
            rumps.MenuItem("Enter Pro License...", callback=self._enter_license),
            rumps.MenuItem("Settings...", callback=self._show_settings),
            rumps.MenuItem(
                "Help",
            ),
            None,
            rumps.MenuItem("Quit SortMeOut", callback=self._quit),
        ]

        # Build Trash submenu (dict-style assignment for proper rumps submenu)
        trash_menu = self.app.menu["Trash"]
        trash_menu["View Trash Status"] = rumps.MenuItem(
            "View Trash Status", callback=self._show_trash_status,
        )
        trash_menu["Empty Trash"] = rumps.MenuItem(
            "Empty Trash", callback=self._empty_trash,
        )

        # Build Help submenu (dict-style assignment for proper rumps submenu)
        help_menu = self.app.menu["Help"]
        help_menu["Documentation"] = rumps.MenuItem(
            "Documentation", callback=self._open_docs,
        )
        help_menu["Report Issue"] = rumps.MenuItem(
            "Report Issue", callback=self._report_issue,
        )
        help_menu[f"About SortMeOut v{__version__}"] = rumps.MenuItem(
            f"About SortMeOut v{__version__}", callback=self._show_about,
        )

        self._update_folders_menu()

    # ──────────────────────────────────────────────────────────────────
    # FOLDERS SUBMENU
    # ──────────────────────────────────────────────────────────────────

    def _update_folders_menu(self) -> None:
        """Update the folders submenu."""
        try:
            folders_menu = self.app.menu.get("Folders")
            if folders_menu is None:
                return

            try:
                folders_menu.clear()
            except (AttributeError, TypeError):
                pass

            folders = self.sortmeout.get_folders()

            if not folders:
                try:
                    folders_menu.add(
                        rumps.MenuItem("No folders configured", callback=None)
                    )
                except Exception:
                    pass
            else:
                for folder in folders:
                    rules = self.sortmeout.get_rules(folder)
                    folder_name = os.path.basename(folder) or folder
                    item = rumps.MenuItem(
                        f"{folder_name} ({len(rules)} rules)",
                        callback=lambda _, f=folder: self._show_folder_details(f),
                    )
                    try:
                        folders_menu.add(item)
                    except Exception:
                        pass

            try:
                folders_menu.add(None)
                folders_menu.add(
                    rumps.MenuItem("Add Folder...", callback=self._add_folder)
                )
            except Exception:
                pass
        except Exception as e:
            logger.warning("Could not update folders menu: %s", e)

    # ──────────────────────────────────────────────────────────────────
    # WATCHING
    # ──────────────────────────────────────────────────────────────────

    def _toggle_watching(self, sender: rumps.MenuItem) -> None:
        """Toggle watching on/off."""
        if self._running:
            self.sortmeout.stop()
            self._running = False
            sender.title = "Start Watching"
            self.app.title = "SortMeOut"
            rumps.notification(
                "SortMeOut", "Stopped", "File watching has been stopped."
            )
        else:
            # License gate
            from sortmeout.core.license import can_watch_filesystem, LicenseAuthority
            if not can_watch_filesystem():
                rumps.alert(
                    title="License Required",
                    message=LicenseAuthority.get_expired_message(),
                )
                return

            folders = self.sortmeout.get_folders()
            if not folders:
                rumps.alert(
                    title="No Folders Configured",
                    message="Add folders first: click 'Add Folder...' under the Folders menu.",
                )
                return

            self.sortmeout.start_background()
            self._running = True
            sender.title = "Stop Watching"
            self.app.title = "SortMeOut ●"
            rumps.notification(
                "SortMeOut",
                "Started",
                f"Watching {len(folders)} folder(s).",
            )

    def _toggle_preview(self, sender: rumps.MenuItem) -> None:
        """Toggle preview mode."""
        self._preview_mode = not self._preview_mode
        self.sortmeout.preview_mode = self._preview_mode
        sender.state = 1 if self._preview_mode else 0
        if self._preview_mode:
            rumps.notification(
                "SortMeOut",
                "Preview Mode",
                "Actions will be logged but not executed.",
            )

    # ──────────────────────────────────────────────────────────────────
    # ORGANIZE NOW
    # ──────────────────────────────────────────────────────────────────

    def _organize_now(self, _) -> None:
        """Batch-process all files in watched folders using the core engine."""
        from sortmeout.core.license import can_execute_automation, LicenseAuthority

        if not can_execute_automation():
            rumps.alert(
                title="License Required",
                message=LicenseAuthority.get_expired_message(),
            )
            return

        folders = self.sortmeout.get_folders()
        if not folders:
            rumps.alert(
                title="No Folders",
                message="Add folders first via the Folders menu.",
            )
            return

        threading.Thread(
            target=self._do_organize, args=(folders,), daemon=True
        ).start()

    def _do_organize(self, folders):
        """Run organization in background with grouped notification summary."""
        total = 0
        folder_results = []
        errors = []

        for folder in folders:
            folder_name = os.path.basename(folder.rstrip("/")) or folder
            try:
                result = self.sortmeout.process_folder(folder)
                processed = result.get("processed", 0)
                matched = result.get("matched", 0)
                total += processed
                if processed > 0 or matched > 0:
                    folder_results.append(f"📁 {folder_name}: {processed} file(s)")
            except Exception as e:
                logger.error("Failed to process folder %s: %s", folder, e)
                errors.append(folder_name)

        # Build grouped summary notification
        if total == 0 and not errors:
            subtitle = "Organization Complete"
            message = "No files needed organization."
        else:
            subtitle = f"Organized {total} file(s) across {len(folders)} folder(s)"
            lines = folder_results[:8]  # Cap at 8 lines for readability
            if errors:
                lines.append(f"⚠️ Errors in: {', '.join(errors)}")
            if len(folder_results) > 8:
                lines.append(f"...and {len(folder_results) - 8} more folder(s)")
            message = "\n".join(lines) if lines else f"Processed {total} file(s)."

        rumps.notification("SortMeOut", subtitle, message)

    # ──────────────────────────────────────────────────────────────────
    # AI ASSISTANT & FILE ANALYSIS
    # ──────────────────────────────────────────────────────────────────

    def _open_ai_assistant(self, _) -> None:
        """Open the AI assistant chat window."""
        try:
            from sortmeout.gui.chat_window import show_chat_window
            show_chat_window()
        except ImportError as e:
            logger.error("Could not import chat_window: %s", e)
            rumps.alert(
                title="AI Assistant",
                message="Could not open AI Assistant.\n\nMake sure all dependencies are installed.",
            )
        except Exception as e:
            logger.error("Failed to open AI assistant: %s", e)
            rumps.alert(title="Error", message=f"Could not open AI Assistant:\n{e}")

    def _analyze_file(self, _) -> None:
        """Analyze a file with AI."""
        script = '''
            tell application "System Events"
                activate
                set theFile to choose file with prompt "Select a file to analyze:"
                return POSIX path of theFile
            end tell
        '''
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0 and result.stdout.strip():
                file_path = result.stdout.strip()
                try:
                    from sortmeout.ai.assistant import FileAssistant
                    assistant = FileAssistant()
                    analysis = assistant.analyze_file(file_path)
                    rumps.alert(
                        title=f"Analysis: {os.path.basename(file_path)}",
                        message=analysis.get("summary", analysis.get("analysis", "No summary available.")),
                    )
                except ImportError:
                    rumps.alert(
                        title="AI Not Available",
                        message="AI Assistant requires the anthropic package.\n\nRun: pip install anthropic",
                    )
                except Exception as e:
                    rumps.alert(
                        title="Analysis Failed",
                        message=f"Could not analyze file:\n{e}",
                    )
        except Exception as e:
            logger.error("Failed to analyze file: %s", e)

    # ──────────────────────────────────────────────────────────────────
    # RULE MANAGEMENT
    # ──────────────────────────────────────────────────────────────────

    def _quick_add_rule(self, _) -> None:
        """Quick add a simple extension-based rule."""
        script = '''
        tell application "System Events"
            activate
            set dialogResult to display dialog "Quick Add Rule\n\nEnter a file extension to organize (e.g., pdf, jpg, docx):" default answer "pdf" buttons {"Cancel", "Add Rule"} default button "Add Rule" with title "SortMeOut - Quick Add"
            if button returned of dialogResult is "Add Rule" then
                return text returned of dialogResult
            else
                return ""
            end if
        end tell
        '''
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True
        )
        extension = result.stdout.strip()
        if not extension:
            return
        extension = extension.lower().lstrip(".")

        dest_script = f'''
        tell application "System Events"
            activate
            set destFolder to choose folder with prompt "Choose destination for .{extension} files:"
            return POSIX path of destFolder
        end tell
        '''
        result2 = subprocess.run(
            ["osascript", "-e", dest_script], capture_output=True, text=True
        )
        destination = result2.stdout.strip()
        if not destination:
            return

        src_script = '''
        tell application "System Events"
            activate
            set srcFolder to choose folder with prompt "Choose folder to watch (e.g., Downloads):"
            return POSIX path of srcFolder
        end tell
        '''
        result3 = subprocess.run(
            ["osascript", "-e", src_script], capture_output=True, text=True
        )
        source = result3.stdout.strip()
        if not source:
            return

        from sortmeout.core.rule import Rule
        from sortmeout.core.condition import Condition
        from sortmeout.core.action import Action

        self.sortmeout.add_folder(source)
        rule = Rule(
            name=f"Move .{extension} files",
            conditions=[Condition("extension", "equals", extension)],
            actions=[Action("move", destination=destination)],
        )
        self.sortmeout.add_rule(source, rule)
        self._update_folders_menu()

        rumps.notification(
            "SortMeOut",
            "Rule Added",
            f"Move .{extension} files → {os.path.basename(destination.rstrip('/'))}",
        )

    def _advanced_rule_editor(self, _) -> None:
        """Open the advanced rule editor."""
        try:
            from sortmeout.gui.rule_editor import show_rule_editor

            def on_rule_saved(rule_data):
                from sortmeout.core.rule import Rule
                from sortmeout.core.condition import Condition
                from sortmeout.core.action import Action

                folder = rule_data.get("folder_hint", "")
                if not folder:
                    folders = self.sortmeout.get_folders()
                    if folders:
                        folder = folders[0]

                if folder:
                    conditions = [
                        Condition(c["attribute"], c["operator"], c.get("value", ""))
                        for c in rule_data.get("conditions", [])
                    ]
                    actions = [
                        Action(a["action_type"], **a.get("params", {}))
                        for a in rule_data.get("actions", [])
                    ]
                    rule = Rule(
                        name=rule_data.get("name", "Untitled Rule"),
                        conditions=conditions,
                        actions=actions,
                    )
                    self.sortmeout.add_rule(folder, rule)
                    self._update_folders_menu()

                rumps.notification(
                    "SortMeOut",
                    "Rule Created",
                    f"Rule '{rule_data.get('name', 'Untitled')}' created.",
                )

            show_rule_editor(on_save=on_rule_saved)
        except ImportError:
            rumps.alert(
                title="Not Available",
                message="Advanced Rule Editor requires PyObjC.\nUse Quick Add Rule instead.",
            )

    # ──────────────────────────────────────────────────────────────────
    # ACTIVITY
    # ──────────────────────────────────────────────────────────────────

    def _show_activity(self, _) -> None:
        """Show recent activity from history DB."""
        try:
            from sortmeout.core.history import get_history
            history = get_history()
            recent = history.get_recent(limit=10)

            if not recent:
                rumps.alert(
                    title="Recent Activity",
                    message="No recent activity recorded.",
                )
                return

            lines = []
            for entry in recent:
                status = "✓" if entry.success else "✗"
                dt = entry.timestamp_dt.strftime("%m/%d %H:%M")
                lines.append(f"[{status}] {dt}  {entry.action_type}: {entry.source_name}")

            stats = history.get_statistics(days=7)
            summary = (
                f"Last 7 days: {stats['total_actions']} actions, "
                f"{stats['successful']} succeeded, {stats['errors']} errors\n\n"
            )

            rumps.alert(
                title="Recent Activity",
                message=summary + "\n".join(lines[:10]),
            )
        except Exception:
            stats = self.sortmeout.get_stats()
            rumps.alert(
                title="Recent Activity",
                message=(
                    f"Files processed: {stats['files_processed']}\n"
                    f"Rules matched: {stats['rules_matched']}\n"
                    f"Actions executed: {stats['actions_executed']}\n"
                    f"Errors: {stats['errors']}"
                ),
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
            cancel="Process Now",
        )
        if response == 0:
            self.sortmeout.process_folder(folder)
            rumps.notification(
                "SortMeOut",
                "Processing Complete",
                f"Processed files in {os.path.basename(folder)}",
            )

    def _add_folder(self, _) -> None:
        """Add a folder via native file picker."""
        script = '''
            tell application "System Events"
                activate
                set theFolder to choose folder with prompt "Select a folder to watch:"
                return POSIX path of theFolder
            end tell
        '''
        try:
            result = subprocess.run(
                ["osascript", "-e", script], capture_output=True, text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                folder = result.stdout.strip()
                if self.sortmeout.add_folder(folder):
                    self._update_folders_menu()
                    rumps.notification(
                        "SortMeOut",
                        "Folder Added",
                        f"Now watching: {os.path.basename(folder)}",
                    )
        except Exception as e:
            logger.error("Failed to add folder: %s", e)

    # ──────────────────────────────────────────────────────────────────
    # TRASH
    # ──────────────────────────────────────────────────────────────────

    def _show_trash_status(self, _) -> None:
        """Show Trash status."""
        info = get_trash_info()
        rumps.alert(
            title="Trash Status",
            message=(
                f"Items: {info.item_count}\n"
                f"Size: {info.size_human}\n"
                f"Oldest item: {info.oldest_item_date.strftime('%Y-%m-%d') if info.oldest_item_date else 'N/A'}"
            ),
        )

    def _empty_trash(self, _) -> None:
        """Empty the Trash."""
        response = rumps.alert(
            title="Empty Trash",
            message="Are you sure you want to empty the Trash? This cannot be undone.",
            ok="Empty Trash",
            cancel="Cancel",
        )
        if response == 1:
            if empty_trash():
                rumps.notification(
                    "SortMeOut", "Trash Emptied", "The Trash has been emptied."
                )

    # ──────────────────────────────────────────────────────────────────
    # LICENSE
    # ──────────────────────────────────────────────────────────────────

    def _enter_license(self, _) -> None:
        """Show license entry dialog."""
        from sortmeout.core.license import get_license, LicenseState

        license_auth = get_license()
        if license_auth.state == LicenseState.PRO_ACTIVE:
            rumps.alert(
                title="Pro License Active",
                message="Your Pro license is already active.\n\nThank you for supporting SortMeOut!",
            )
            return

        response = rumps.alert(
            title="Activate Pro License",
            message=(
                "Enter your Pro license key to unlock all features.\n\n"
                "Don't have a key yet? Click 'Get Pro License' to subscribe ($9.99/month).\n\n"
                "Already paid? Check your email for the license key."
            ),
            ok="Enter License Key",
            cancel="Cancel",
            other="Get Pro License",
        )

        if response == 1:
            script = '''
                tell application "System Events"
                    display dialog "Enter your Pro license key:" default answer "" with title "SortMeOut Pro License" buttons {"Cancel", "Activate"} default button "Activate"
                    set theAnswer to text returned of result
                    return theAnswer
                end tell
            '''
            try:
                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if result.returncode == 0 and result.stdout.strip():
                    key = result.stdout.strip()
                    if license_auth.activate_pro_license(key):
                        rumps.alert(
                            title="Pro License Activated! 🎉",
                            message="Thank you for supporting SortMeOut!\n\nAll Pro features are now unlocked.",
                        )
                    else:
                        rumps.alert(
                            title="Invalid License Key",
                            message="The license key you entered is not valid.\nPlease check your email and try again.",
                        )
            except Exception as e:
                rumps.alert(
                    title="Error",
                    message=f"Could not process license key:\n{e}",
                )
        elif response == 0:
            webbrowser.open("https://sortmeout.saidborna.com/#pricing")

    # ──────────────────────────────────────────────────────────────────
    # SETTINGS WINDOW
    # ──────────────────────────────────────────────────────────────────

    def _show_settings(self, _) -> None:
        """Open the native settings window."""
        try:
            from sortmeout.gui.settings_window import show_settings_window
            show_settings_window(self._config_manager, self._on_settings_changed)
        except ImportError:
            rumps.alert(
                title="Settings",
                message="Settings window requires PyObjC.\n\nUse the CLI instead:\nsortmeout config show",
            )
        except Exception as e:
            logger.error("Failed to open settings: %s", e)
            rumps.alert(title="Error", message=f"Could not open settings:\n{e}")

    def _on_settings_changed(self, settings):
        """Handle settings changes."""
        self._settings = settings
        self._config_manager.save_settings(settings)

    # ──────────────────────────────────────────────────────────────────
    # FIRST-RUN ONBOARDING
    # ──────────────────────────────────────────────────────────────────

    def _run_onboarding(self, _) -> None:
        """Run first-launch onboarding flow."""
        try:
            from sortmeout.gui.onboarding import run_onboarding
            run_onboarding(self.sortmeout, self._config_manager, self._update_folders_menu)
        except ImportError:
            response = rumps.alert(
                title="Welcome to SortMeOut! 👋",
                message=(
                    "SortMeOut automatically organizes your files using smart rules.\n\n"
                    "To get started:\n"
                    "1. Add a folder to watch (e.g., Downloads)\n"
                    "2. Create rules or use templates\n"
                    "3. Click 'Start Watching'\n\n"
                    "Would you like to add your first folder now?"
                ),
                ok="Add Folder",
                cancel="Later",
            )
            if response == 1:
                self._add_folder(None)
        except Exception as e:
            logger.error("Onboarding failed: %s", e)

    # ──────────────────────────────────────────────────────────────────
    # HELP / ABOUT
    # ──────────────────────────────────────────────────────────────────

    def _open_docs(self, _) -> None:
        """Open documentation."""
        webbrowser.open("https://sortmeout.saidborna.com/docs")

    def _report_issue(self, _) -> None:
        """Open issue tracker."""
        webbrowser.open("https://github.com/S-Borna/sortmeout/issues")

    def _show_about(self, _) -> None:
        """Show about dialog."""
        rumps.alert(
            title="About SortMeOut",
            message=(
                f"SortMeOut v{__version__}\n\n"
                "Intelligent file automation for macOS.\n"
                "Automatically organize your files with powerful rules.\n\n"
                "© 2026 Said Borna\n"
                "Proprietary License\n\n"
                "https://sortmeout.saidborna.com"
            ),
        )

    # ──────────────────────────────────────────────────────────────────
    # STATUS / QUIT
    # ──────────────────────────────────────────────────────────────────

    def _update_status(self, _) -> None:
        """Periodic status update — flush batched notifications as grouped summary."""
        with self._notification_lock:
            if not self._notification_queue:
                return
            events = list(self._notification_queue)
            self._notification_queue.clear()

        # Group events by folder
        folder_counts: dict[str, int] = {}
        for event in events:
            folder = event.get("folder", "Unknown")
            folder_counts[folder] = folder_counts.get(folder, 0) + 1

        total = sum(folder_counts.values())
        lines = [
            f"📁 {os.path.basename(f.rstrip('/'))}: {c} file(s)"
            for f, c in folder_counts.items()
        ]

        subtitle = f"{total} file(s) organized"
        message = "\n".join(lines[:6])
        if len(lines) > 6:
            message += f"\n...and {len(lines) - 6} more folder(s)"

        rumps.notification("SortMeOut", subtitle, message)

    def record_file_event(self, folder: str, file_path: str) -> None:
        """Record a file event for batched notification delivery."""
        with self._notification_lock:
            self._notification_queue.append({
                "folder": folder,
                "file": file_path,
                "time": time.time(),
            })

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
