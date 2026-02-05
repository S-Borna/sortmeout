"""
Main Window for SortMeOut - Hazel-like rule management.
Uses PyObjC for native macOS UI.
"""

import os
import sys
import json
import threading
from pathlib import Path

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Import rule editor
try:
    from sortmeout.gui.rule_editor import show_rule_editor

    HAS_RULE_EDITOR = True
except ImportError:
    HAS_RULE_EDITOR = False
try:
    import rumps
    from AppKit import (
        NSApplication,
        NSApp,
        NSWindow,
        NSWindowStyleMaskTitled,
        NSWindowStyleMaskClosable,
        NSWindowStyleMaskResizable,
        NSWindowStyleMaskMiniaturizable,
        NSBackingStoreBuffered,
        NSTableView,
        NSTableColumn,
        NSScrollView,
        NSButton,
        NSTextField,
        NSFont,
        NSColor,
        NSView,
        NSStackView,
        NSUserInterfaceLayoutOrientationVertical,
        NSUserInterfaceLayoutOrientationHorizontal,
        NSPopUpButton,
        NSComboBox,
        NSAlert,
        NSAlertStyleInformational,
        NSOpenPanel,
        NSModalResponseOK,
        NSBezelStyleRounded,
        NSSplitView,
        NSOutlineView,
        NSImage,
        NSImageNameFolder,
        NSLayoutConstraint,
        NSMenuItem,
        NSMenu,
        NSStatusBar,
    )
    from Foundation import NSObject, NSRect, NSPoint, NSSize, NSMakeRect

    HAS_APPKIT = True
except ImportError:
    HAS_APPKIT = False
    print("AppKit not available")


# Config file path
CONFIG_DIR = os.path.expanduser("~/.config/sortmeout")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")


def ensure_config_dir():
    """Ensure config directory exists."""
    os.makedirs(CONFIG_DIR, exist_ok=True)


def load_config():
    """Load configuration from file."""
    ensure_config_dir()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"folders": [], "rules": []}


def save_config(config):
    """Save configuration to file."""
    ensure_config_dir()
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


class SortMeOutApp(rumps.App):
    """Main menu bar application."""

    def __init__(self):
        # Import license authority
        from sortmeout.core.license import get_license

        self.license = get_license()

        super().__init__("SortMeOut", title="○", quit_button=None)

        self.config = load_config()
        self.watching = False
        self.watcher = None

        # Build menu with license status
        self.menu = [
            rumps.MenuItem(f"{self.license.get_status_message()}"),
            None,  # Separator
            rumps.MenuItem("AI Assistant..."),
            rumps.MenuItem("Analyze File..."),
            None,  # Separator
            rumps.MenuItem("Start Watching"),
            rumps.MenuItem("Organize Now"),
            None,  # Separator
            rumps.MenuItem("Manage Folders & Rules..."),
            rumps.MenuItem("Quick Add Rule..."),
            rumps.MenuItem("Advanced Rule Editor..."),
            None,
            rumps.MenuItem("Enter Pro License..."),
            rumps.MenuItem("Open Config Folder"),
            rumps.MenuItem("Documentation"),
            None,
            rumps.MenuItem("About SortMeOut"),
            rumps.MenuItem("Quit"),
        ]

    @rumps.clicked("AI Assistant...")
    def open_ai_assistant(self, _):
        """Open the AI assistant chat window."""
        try:
            from sortmeout.gui.chat_window import show_chat_window
            show_chat_window()
        except Exception as e:
            rumps.alert(
                title="AI Assistant",
                message=f"Could not open AI Assistant:\n{e}"
            )

    @rumps.clicked("Analyze File...")
    def analyze_file(self, _):
        """Analyze a file with AI."""
        import subprocess

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
                        message=analysis.get("summary", "Could not analyze file.")
                    )
                except ImportError:
                    rumps.alert(
                        title="AI Not Available",
                        message="AI Assistant requires the anthropic package."
                    )
                except Exception as e:
                    rumps.alert(
                        title="Analysis Failed",
                        message=f"Could not analyze file:\n{e}"
                    )
        except Exception as e:
            pass

    @rumps.clicked("Enter Pro License...")
    def enter_license(self, _):
        """Show license entry dialog."""
        from sortmeout.core.license import get_license, LicenseState

        license_auth = get_license()

        if license_auth.state == LicenseState.PRO_ACTIVE:
            rumps.alert(
                title="Pro License Active",
                message="Your Pro license is already active.\n\nThank you for supporting SortMeOut!",
            )
            return

        # Simple license entry via alert (rumps doesn't have text input)
        rumps.alert(
            title="Enter Pro License",
            message=(
                "To enter your Pro license key, add it to:\n\n"
                f"{CONFIG_DIR}/license.json\n\n"
                'Format: {"pro_license_key": "YOUR-KEY-HERE"}\n\n'
                "Get your license at: sortmeout.saidborna.com"
            ),
        )

    @rumps.clicked("Start Watching")
    def toggle_watching(self, sender):
        """Toggle file watching."""
        if not self.watching:
            self.start_watching(sender)
        else:
            self.stop_watching(sender)

    @rumps.clicked("Stop Watching")
    def stop_watching_menu(self, sender):
        """Stop watching (alternate menu title)."""
        self.stop_watching(sender)

    def start_watching(self, sender):
        """Start file watching."""
        # LICENSE GATE: Check if watching is allowed
        from sortmeout.core.license import can_watch_filesystem, LicenseAuthority

        if not can_watch_filesystem():
            rumps.alert(title="License Required", message=LicenseAuthority.get_expired_message())
            return

        self.config = load_config()

        if not self.config.get("folders") or not self.config.get("rules"):
            rumps.alert(
                title="No Rules Configured",
                message="Please add folders and rules first.\n\nClick 'Manage Folders & Rules...' to get started.",
            )
            return

        try:
            from sortmeout.app import SortMeOut

            self.watcher = SortMeOut()

            # Add folders and rules from config
            for folder in self.config.get("folders", []):
                self.watcher.add_folder(folder)

            self.watcher.start()
            self.watching = True
            sender.title = "Stop Watching"
            self.title = "●"

            folder_count = len(self.config.get("folders", []))
            rule_count = len(self.config.get("rules", []))

            rumps.notification(
                title="SortMeOut",
                subtitle="Watching Started",
                message=f"Monitoring {folder_count} folder(s) with {rule_count} rule(s).",
            )
        except Exception as e:
            rumps.alert(title="Error", message=f"Could not start watcher:\n{e}")

    def stop_watching(self, sender):
        """Stop file watching."""
        if self.watcher:
            try:
                self.watcher.stop()
            except:
                pass
            self.watcher = None

        self.watching = False
        sender.title = "Start Watching"
        self.title = "○"

        rumps.notification(
            title="SortMeOut",
            subtitle="Watching Stopped",
            message="File monitoring has been stopped.",
        )

    @rumps.clicked("Organize Now")
    def organize_now(self, _):
        """Organize all existing files based on rules."""
        # LICENSE GATE: Check if automation is allowed
        from sortmeout.core.license import can_execute_automation, LicenseAuthority

        if not can_execute_automation():
            rumps.alert(title="License Required", message=LicenseAuthority.get_expired_message())
            return

        self.config = load_config()

        if not self.config.get("rules"):
            rumps.alert(
                title="No Rules Configured",
                message="Please add rules first.\n\nClick 'Quick Add Rule...' to get started.",
            )
            return

        # Run organization in background thread
        threading.Thread(target=self._run_organization, daemon=True).start()

    def _run_organization(self):
        """Run the actual organization process."""
        config = self.config
        rules = config.get("rules", [])
        folders = config.get("folders", [])

        if not folders:
            rumps.notification(
                title="SortMeOut",
                subtitle="No Folders",
                message="No folders configured to organize.",
            )
            return

        total_moved = 0
        total_errors = 0

        for folder in folders:
            folder_path = os.path.expanduser(folder)
            if not os.path.isdir(folder_path):
                continue

            # Get all files in folder
            try:
                files = [
                    f
                    for f in os.listdir(folder_path)
                    if os.path.isfile(os.path.join(folder_path, f)) and not f.startswith(".")
                ]
            except Exception as e:
                total_errors += 1
                continue

            for filename in files:
                filepath = os.path.join(folder_path, filename)

                # Check each rule
                for rule in rules:
                    if not rule.get("enabled", True):
                        continue

                    # Check if rule applies to this folder
                    rule_folder = os.path.expanduser(rule.get("folder", ""))
                    if rule_folder and rule_folder.rstrip("/") != folder_path.rstrip("/"):
                        continue

                    # Check conditions
                    if self._file_matches_rule(filepath, rule):
                        # Execute actions
                        result = self._execute_rule_actions(filepath, rule)
                        if result:
                            total_moved += 1
                        else:
                            total_errors += 1
                        break  # Only first matching rule

        # Show result
        if total_moved > 0:
            rumps.notification(
                title="SortMeOut",
                subtitle="Organization Complete",
                message=f"Organized {total_moved} file(s).",
            )
        else:
            rumps.notification(
                title="SortMeOut",
                subtitle="Organization Complete",
                message="No files needed organization.",
            )

    def _file_matches_rule(self, filepath, rule):
        """Check if a file matches a rule's conditions."""
        filename = os.path.basename(filepath)
        conditions = rule.get("conditions", [])

        if not conditions:
            return True  # No conditions = match all

        for condition in conditions:
            cond_type = condition.get("type", "")
            operator = condition.get("operator", "equals")
            value = condition.get("value", "")

            if cond_type == "extension":
                ext = os.path.splitext(filename)[1].lower().lstrip(".")
                if operator == "equals" and ext != value.lower().lstrip("."):
                    return False
                if operator == "contains" and value.lower() not in ext:
                    return False

            elif cond_type == "name":
                name = filename.lower()
                if operator == "equals" and name != value.lower():
                    return False
                if operator == "contains" and value.lower() not in name:
                    return False
                if operator == "starts_with" and not name.startswith(value.lower()):
                    return False
                if operator == "ends_with" and not name.endswith(value.lower()):
                    return False

            elif cond_type == "size":
                try:
                    size = os.path.getsize(filepath)
                    # Parse value like "10MB", "1GB"
                    threshold = self._parse_size(value)
                    if operator == "greater_than" and size <= threshold:
                        return False
                    if operator == "less_than" and size >= threshold:
                        return False
                except:
                    return False

        return True

    def _parse_size(self, size_str):
        """Parse size string like '10MB' to bytes."""
        size_str = str(size_str).upper().strip()
        multipliers = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
        for suffix, mult in multipliers.items():
            if size_str.endswith(suffix):
                return int(float(size_str[: -len(suffix)]) * mult)
        return int(size_str)

    def _execute_rule_actions(self, filepath, rule):
        """Execute a rule's actions on a file."""
        actions = rule.get("actions", [])

        for action in actions:
            action_type = action.get("type", "")

            if action_type == "move":
                destination = os.path.expanduser(action.get("destination", ""))
                if destination:
                    try:
                        os.makedirs(destination, exist_ok=True)
                        filename = os.path.basename(filepath)
                        dest_path = os.path.join(destination, filename)

                        # Handle duplicates
                        if os.path.exists(dest_path):
                            base, ext = os.path.splitext(filename)
                            counter = 1
                            while os.path.exists(dest_path):
                                dest_path = os.path.join(destination, f"{base} ({counter}){ext}")
                                counter += 1

                        import shutil

                        shutil.move(filepath, dest_path)
                        return True
                    except Exception as e:
                        print(f"Move error: {e}")
                        return False

            elif action_type == "copy":
                destination = os.path.expanduser(action.get("destination", ""))
                if destination:
                    try:
                        os.makedirs(destination, exist_ok=True)
                        filename = os.path.basename(filepath)
                        dest_path = os.path.join(destination, filename)

                        import shutil

                        shutil.copy2(filepath, dest_path)
                        return True
                    except Exception as e:
                        print(f"Copy error: {e}")
                        return False

            elif action_type == "trash":
                try:
                    # Move to macOS Trash
                    import subprocess

                    subprocess.run(
                        [
                            "osascript",
                            "-e",
                            f'tell application "Finder" to delete POSIX file "{filepath}"',
                        ],
                        check=True,
                    )
                    return True
                except Exception as e:
                    print(f"Trash error: {e}")
                    return False

            elif action_type == "rename":
                new_name = action.get("new_name", "")
                if new_name:
                    try:
                        directory = os.path.dirname(filepath)
                        new_path = os.path.join(directory, new_name)
                        os.rename(filepath, new_path)
                        return True
                    except Exception as e:
                        print(f"Rename error: {e}")
                        return False

        return False

    @rumps.clicked("Manage Folders & Rules...")
    def manage_rules(self, _):
        """Open the rule management window."""
        if HAS_APPKIT:
            show_management_window(self.config, self.reload_config)
        else:
            # Fallback: open config file
            os.system(f'open "{CONFIG_FILE}"')

    @rumps.clicked("Quick Add Rule...")
    def quick_add_rule(self, _):
        """Quick add a simple rule."""
        show_quick_rule_dialog(self.config, self.reload_config)

    @rumps.clicked("Advanced Rule Editor...")
    def advanced_rule_editor(self, _):
        """Open the advanced rule editor window."""
        if HAS_RULE_EDITOR:

            def on_rule_saved(rule_data):
                """Handle saved rule from editor."""
                # Add to config
                self.config.setdefault("rules", []).append(rule_data)
                save_config(self.config)
                self.reload_config()

                rumps.notification(
                    title="SortMeOut",
                    subtitle="Rule Created",
                    message=f"Rule '{rule_data['name']}' has been created.",
                )

            show_rule_editor(on_save=on_rule_saved)
        else:
            rumps.alert(
                title="Not Available",
                message="Advanced Rule Editor requires PyObjC.\nPlease use Quick Add Rule instead.",
            )

    @rumps.clicked("Open Config Folder")
    def open_config(self, _):
        """Open config folder in Finder."""
        ensure_config_dir()
        os.system(f'open "{CONFIG_DIR}"')

    @rumps.clicked("Documentation")
    def open_docs(self, _):
        """Open documentation website."""
        os.system('open "https://sortmeout.saidborna.com"')

    @rumps.clicked("About SortMeOut")
    def show_about(self, _):
        """Show about dialog."""
        rumps.alert(
            title="About SortMeOut",
            message="SortMeOut v1.0.1\n\nIntelligent file automation for macOS.\nAutomatically organize your files with powerful rules.\n\n© 2026 Said Borna\nProprietary License\n\nhttps://sortmeout.saidborna.com",
        )

    @rumps.clicked("Quit")
    def quit_app(self, _):
        """Quit the application."""
        if self.watcher:
            try:
                self.watcher.stop()
            except:
                pass
        rumps.quit_application()

    def reload_config(self):
        """Reload configuration from file."""
        self.config = load_config()


def show_quick_rule_dialog(config, reload_callback):
    """Show a simple dialog to quickly add a rule."""
    import subprocess

    # Use AppleScript for a simple dialog
    script = """
    tell application "System Events"
        activate
        set dialogResult to display dialog "Quick Add Rule

Enter a file extension to organize (e.g., pdf, jpg, docx):" default answer "pdf" buttons {"Cancel", "Add Rule"} default button "Add Rule" with title "SortMeOut - Quick Add"

        if button returned of dialogResult is "Add Rule" then
            return text returned of dialogResult
        else
            return ""
        end if
    end tell
    """

    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    extension = result.stdout.strip()

    if not extension:
        return

    # Clean extension
    extension = extension.lower().lstrip(".")

    # Ask for destination
    script2 = f"""
    tell application "System Events"
        activate
        set destFolder to choose folder with prompt "Choose destination folder for .{extension} files:"
        return POSIX path of destFolder
    end tell
    """

    result2 = subprocess.run(["osascript", "-e", script2], capture_output=True, text=True)
    destination = result2.stdout.strip()

    if not destination:
        return

    # Ask for source folder
    script3 = """
    tell application "System Events"
        activate
        set srcFolder to choose folder with prompt "Choose folder to watch (e.g., Downloads):"
        return POSIX path of srcFolder
    end tell
    """

    result3 = subprocess.run(["osascript", "-e", script3], capture_output=True, text=True)
    source = result3.stdout.strip()

    if not source:
        return

    # Add to config
    if source not in config.get("folders", []):
        config.setdefault("folders", []).append(source)

    rule = {
        "name": f"Move .{extension} files",
        "folder": source,
        "conditions": [{"type": "extension", "operator": "equals", "value": extension}],
        "actions": [{"type": "move", "destination": destination}],
        "enabled": True,
    }

    config.setdefault("rules", []).append(rule)
    save_config(config)
    reload_callback()

    rumps.notification(
        title="SortMeOut",
        subtitle="Rule Added",
        message=f"New rule: Move .{extension} files to {os.path.basename(destination.rstrip('/'))}",
    )


def show_management_window(config, reload_callback):
    """Show the main management window using AppleScript for simplicity."""
    import subprocess

    # Get current rules summary
    folders = config.get("folders", [])
    rules = config.get("rules", [])

    folders_text = "\n".join([f"• {f}" for f in folders]) if folders else "No folders configured"
    rules_text = (
        "\n".join([f"• {r.get('name', 'Unnamed')}" for r in rules])
        if rules
        else "No rules configured"
    )

    message = f"""WATCHED FOLDERS:
{folders_text}

RULES:
{rules_text}

What would you like to do?"""

    script = f"""
    tell application "System Events"
        activate
        set dialogResult to display dialog "{message}" buttons {{"Add Folder", "Add Rule", "Edit Config"}} default button "Add Rule" with title "SortMeOut - Manage"
        return button returned of dialogResult
    end tell
    """

    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    choice = result.stdout.strip()

    if choice == "Add Folder":
        add_folder_dialog(config, reload_callback)
    elif choice == "Add Rule":
        show_quick_rule_dialog(config, reload_callback)
    elif choice == "Edit Config":
        # Create config if it doesn't exist
        if not os.path.exists(CONFIG_FILE):
            save_config(config)
        os.system(f'open -a TextEdit "{CONFIG_FILE}"')


def add_folder_dialog(config, reload_callback):
    """Add a folder to watch."""
    import subprocess

    script = """
    tell application "System Events"
        activate
        set watchFolder to choose folder with prompt "Choose a folder to watch:"
        return POSIX path of watchFolder
    end tell
    """

    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    folder = result.stdout.strip()

    if folder and folder not in config.get("folders", []):
        config.setdefault("folders", []).append(folder)
        save_config(config)
        reload_callback()

        rumps.notification(
            title="SortMeOut",
            subtitle="Folder Added",
            message=f"Now watching: {os.path.basename(folder.rstrip('/'))}",
        )


def main():
    """Main entry point."""
    app = SortMeOutApp()
    app.run()


if __name__ == "__main__":
    main()
