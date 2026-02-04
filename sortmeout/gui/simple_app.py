"""
Simple macOS Menu Bar application for SortMeOut.
"""

import sys
import os

# Add parent to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    """Main entry point."""
    try:
        import rumps
    except ImportError:
        # Show error dialog
        import subprocess

        subprocess.run(
            [
                "osascript",
                "-e",
                'display dialog "SortMeOut requires rumps to be installed.\\n\\nRun: pip install sortmeout" buttons {"OK"} default button "OK" with title "SortMeOut Error"',
            ]
        )
        sys.exit(1)

    class SortMeOutApp(rumps.App):
        def __init__(self):
            super().__init__("SortMeOut", title="📂", quit_button=None)  # Use emoji as icon
            self.watching = False
            self.watcher = None

            # Create menu items
            self.start_button = rumps.MenuItem("▶ Start Watching")
            self.menu = [
                self.start_button,
                None,
                rumps.MenuItem("📁 Open Config Folder"),
                rumps.MenuItem("📖 Documentation"),
                None,
                rumps.MenuItem("ℹ️ About SortMeOut"),
                rumps.MenuItem("❌ Quit"),
            ]

        @rumps.clicked("▶ Start Watching")
        def toggle_watching(self, sender):
            try:
                if not self.watching:
                    # Start watching
                    self.watching = True
                    sender.title = "⏹ Stop Watching"
                    self.title = "📂✓"

                    # Try to start actual watcher
                    try:
                        from sortmeout.app import SortMeOut

                        self.watcher = SortMeOut()
                        self.watcher.start()
                    except Exception as e:
                        print(f"Watcher error: {e}")

                    rumps.notification(
                        title="SortMeOut",
                        subtitle="Watching Started",
                        message="SortMeOut is now monitoring your folders.",
                    )
                else:
                    # Stop watching
                    self.watching = False
                    sender.title = "▶ Start Watching"
                    self.title = "📂"

                    if self.watcher:
                        try:
                            self.watcher.stop()
                        except:
                            pass
                        self.watcher = None

                    rumps.notification(
                        title="SortMeOut",
                        subtitle="Watching Stopped",
                        message="SortMeOut has stopped monitoring.",
                    )
            except Exception as e:
                rumps.alert(f"Error: {e}")

        @rumps.clicked("⏹ Stop Watching")
        def stop_watching(self, sender):
            self.toggle_watching(sender)

        @rumps.clicked("📁 Open Config Folder")
        def open_config(self, _):
            import subprocess

            config_path = os.path.expanduser("~/.config/sortmeout")
            os.makedirs(config_path, exist_ok=True)
            subprocess.run(["open", config_path])

        @rumps.clicked("📖 Documentation")
        def open_docs(self, _):
            import subprocess

            subprocess.run(["open", "https://sortmeout.saidborna.com"])

        @rumps.clicked("ℹ️ About SortMeOut")
        def show_about(self, _):
            rumps.alert(
                title="About SortMeOut",
                message="SortMeOut v1.0.0\n\nAutomatic file organization for macOS.\n\n© 2026 SortMeOut Contributors\nMIT License\n\nhttps://sortmeout.saidborna.com",
            )

        @rumps.clicked("❌ Quit")
        def quit_app(self, _):
            if self.watcher:
                try:
                    self.watcher.stop()
                except:
                    pass
            rumps.quit_application()

    app = SortMeOutApp()
    app.run()


if __name__ == "__main__":
    main()
