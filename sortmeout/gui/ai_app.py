"""
AI-powered GUI for SortMeOut with chat interface and drag-drop.
"""

import os
import sys
import json
import threading
import subprocess
from pathlib import Path
from datetime import datetime

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import rumps

# Config paths
CONFIG_DIR = os.path.expanduser("~/.config/sortmeout")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
API_KEY_FILE = os.path.join(CONFIG_DIR, "api_key")
ENV_FILE = os.path.join(CONFIG_DIR, ".env")


def ensure_config():
    os.makedirs(CONFIG_DIR, exist_ok=True)


def load_api_key():
    """Load API key from .env file, api_key file, or environment."""
    # First try .env file
    if os.path.exists(ENV_FILE):
        try:
            with open(ENV_FILE, "r") as f:
                for line in f:
                    if line.startswith("ANTHROPIC_API_KEY="):
                        return line.split("=", 1)[1].strip()
        except:
            pass

    # Then try api_key file
    if os.path.exists(API_KEY_FILE):
        with open(API_KEY_FILE, "r") as f:
            return f.read().strip()

    return os.environ.get("ANTHROPIC_API_KEY")


def save_api_key(key):
    """Save API key to file."""
    ensure_config()
    with open(API_KEY_FILE, "w") as f:
        f.write(key)


def load_config():
    ensure_config()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"folders": ["~/Downloads", "~/Desktop"], "rules": [], "ai_enabled": True}


def save_config(config):
    ensure_config()
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


class SortMeOutAI(rumps.App):
    """AI-powered SortMeOut menu bar app."""

    def __init__(self):
        super().__init__("SortMeOut AI", title="🤖", quit_button=None)

        self.config = load_config()
        self.api_key = load_api_key()
        self.assistant = None
        self.watching = False
        self.watcher_thread = None

        # Initialize AI if key exists
        if self.api_key:
            self._init_assistant()

        # Build menu
        self.menu = [
            rumps.MenuItem("💬 Öppna Assistent..."),
            rumps.MenuItem("📎 Analysera Fil..."),
            None,
            rumps.MenuItem("▶ Börja Bevaka"),
            rumps.MenuItem("🔄 Organisera Nu"),
            None,
            rumps.MenuItem("⚙️ Inställningar..."),
            rumps.MenuItem("🔑 API-nyckel..."),
            None,
            rumps.MenuItem("📖 Dokumentation"),
            rumps.MenuItem("ℹ️ Om SortMeOut"),
            rumps.MenuItem("❌ Avsluta"),
        ]

    def _init_assistant(self):
        """Initialize the AI assistant."""
        try:
            from sortmeout.ai.assistant import FileAssistant

            self.assistant = FileAssistant(api_key=self.api_key)
            self.title = "🤖"
        except Exception as e:
            print(f"Could not initialize AI: {e}")
            self.assistant = None
            self.title = "📂"

    @rumps.clicked("💬 Öppna Assistent...")
    def open_chat(self, _):
        """Open chat dialog."""
        if not self.api_key:
            self._prompt_api_key()
            return

        # Open the native chat window
        try:
            from sortmeout.gui.chat_window import show_chat_window

            show_chat_window()
        except Exception as e:
            # Fallback to simple dialog
            print(f"Could not open chat window: {e}")
            self._show_chat_dialog()

    def _show_chat_dialog(self):
        """Show the chat interface using AppleScript."""
        script = """
        tell application "System Events"
            activate
            set userInput to display dialog "🤖 SortMeOut AI Assistent

Skriv vad du vill göra:
• 'Organisera mina nedladdningar'
• 'Var ska jag lägga rapport.pdf?'
• 'Skapa en mapp för skolprojekt'
• 'Visa min mappstruktur'" default answer "" buttons {"Avbryt", "Skicka"} default button "Skicka" with title "SortMeOut AI"

            if button returned of userInput is "Skicka" then
                return text returned of userInput
            else
                return ""
            end if
        end tell
        """

        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        user_message = result.stdout.strip()

        if user_message:
            # Process with AI in background
            threading.Thread(target=self._process_chat, args=(user_message,), daemon=True).start()

    def _process_chat(self, message):
        """Process chat message with AI."""
        try:
            response = self.assistant.chat(message)
            self._show_response(response)
        except Exception as e:
            self._show_response(f"Fel: {str(e)}")

    def _show_response(self, text):
        """Show AI response in a dialog."""
        # Escape quotes for AppleScript
        safe_text = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")

        script = f"""
        tell application "System Events"
            activate
            display dialog "🤖 SortMeOut svarar:\\n\\n{safe_text}" buttons {{"OK", "Fortsätt chatta"}} default button "OK" with title "SortMeOut AI"
            return button returned of result
        end tell
        """

        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        if "Fortsätt" in result.stdout:
            self._show_chat_dialog()

    @rumps.clicked("📎 Analysera Fil...")
    def analyze_file(self, _):
        """Let user select a file to analyze."""
        if not self.api_key:
            self._prompt_api_key()
            return

        if not self.assistant:
            self._init_assistant()

        # File picker
        script = """
        tell application "System Events"
            activate
            set selectedFile to choose file with prompt "Välj en fil att analysera:"
            return POSIX path of selectedFile
        end tell
        """

        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        filepath = result.stdout.strip()

        if filepath:
            threading.Thread(
                target=self._analyze_and_suggest, args=(filepath,), daemon=True
            ).start()

    def _analyze_and_suggest(self, filepath):
        """Analyze file and show suggestions."""
        try:
            suggestion = self.assistant.get_suggestion(filepath)

            if "error" in suggestion:
                self._show_response(f"Fel: {suggestion['error']}")
                return

            # Build suggestion text
            analysis = suggestion.get("analysis", "Kunde inte analysera filen.")
            suggestions = suggestion.get("suggestions", [])

            text = f"📄 {os.path.basename(filepath)}\\n\\n"
            text += f"📊 Analys: {analysis}\\n\\n"
            text += "📁 Förslag:\\n"

            for i, s in enumerate(suggestions[:4]):
                confidence = int(s.get("confidence", 0) * 100)
                text += (
                    f"{i+1}. {s.get('path', '?')} ({confidence}%)\\n   → {s.get('reason', '')}\\n"
                )

            if suggestion.get("question"):
                text += f"\\n❓ {suggestion['question']}"

            self._show_suggestion_dialog(filepath, suggestion, text)

        except Exception as e:
            self._show_response(f"Fel vid analys: {str(e)}")

    def _show_suggestion_dialog(self, filepath, suggestion, text):
        """Show suggestions and let user choose."""
        suggestions = suggestion.get("suggestions", [])

        # Build button list (max 3 suggestions + cancel)
        buttons = []
        for i, s in enumerate(suggestions[:3]):
            path = s.get("path", "?")
            short_path = os.path.basename(path.rstrip("/"))
            buttons.append(f"{i+1}. {short_path}")
        buttons.append("Avbryt")

        button_str = '{"' + '", "'.join(reversed(buttons)) + '"}'
        safe_text = text.replace("\\", "\\\\").replace('"', '\\"')

        script = f"""
        tell application "System Events"
            activate
            set dialogResult to display dialog "{safe_text}" buttons {button_str} default button 1 with title "SortMeOut - Filanalys"
            return button returned of dialogResult
        end tell
        """

        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        choice = result.stdout.strip()

        if choice and choice != "Avbryt":
            # Extract index from choice
            try:
                idx = int(choice[0]) - 1
                if 0 <= idx < len(suggestions):
                    dest = suggestions[idx].get("path", "")
                    self._execute_move(filepath, dest)
            except:
                pass

    def _execute_move(self, filepath, destination):
        """Execute the move action."""
        try:
            result = self.assistant.execute_action(filepath, "move", destination)

            if result.get("success"):
                rumps.notification(
                    title="SortMeOut",
                    subtitle="Fil flyttad!",
                    message=f"{os.path.basename(filepath)} → {destination}",
                )
            else:
                rumps.notification(
                    title="SortMeOut",
                    subtitle="Fel",
                    message=result.get("error", "Kunde inte flytta filen"),
                )
        except Exception as e:
            rumps.notification(title="Fel", subtitle="", message=str(e))

    @rumps.clicked("▶ Börja Bevaka")
    def start_watching(self, sender):
        """Start watching folders for new files."""
        if not self.api_key:
            self._prompt_api_key()
            return

        if not self.watching:
            self.watching = True
            sender.title = "⏹ Sluta Bevaka"
            self.title = "🤖✓"

            # Start watcher thread
            self.watcher_thread = threading.Thread(target=self._watch_folders, daemon=True)
            self.watcher_thread.start()

            rumps.notification(
                title="SortMeOut AI",
                subtitle="Bevakning startad",
                message="Jag övervakar nu dina mappar och hjälper dig organisera nya filer.",
            )
        else:
            self.watching = False
            sender.title = "▶ Börja Bevaka"
            self.title = "🤖"

            rumps.notification(
                title="SortMeOut AI",
                subtitle="Bevakning stoppad",
                message="Filövervakning har stoppats.",
            )

    @rumps.clicked("⏹ Sluta Bevaka")
    def stop_watching(self, sender):
        """Stop watching (alternate title)."""
        self.start_watching(sender)

    def _watch_folders(self):
        """Watch folders for new files."""
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler

            class NewFileHandler(FileSystemEventHandler):
                def __init__(handler_self, app):
                    handler_self.app = app
                    handler_self.processed = set()

                def on_created(handler_self, event):
                    if event.is_directory:
                        return

                    filepath = event.src_path

                    # Skip hidden files and already processed
                    if os.path.basename(filepath).startswith("."):
                        return
                    if filepath in handler_self.processed:
                        return

                    handler_self.processed.add(filepath)

                    # Wait a bit for file to finish writing
                    import time

                    time.sleep(1)

                    if os.path.exists(filepath):
                        handler_self.app._on_new_file(filepath)

            observer = Observer()
            handler = NewFileHandler(self)

            folders = self.config.get("folders", ["~/Downloads", "~/Desktop"])
            for folder in folders:
                folder_path = os.path.expanduser(folder)
                if os.path.isdir(folder_path):
                    observer.schedule(handler, folder_path, recursive=False)

            observer.start()

            while self.watching:
                import time

                time.sleep(1)

            observer.stop()
            observer.join()

        except Exception as e:
            print(f"Watcher error: {e}")

    def _on_new_file(self, filepath):
        """Handle new file detection."""
        # Show notification and offer to analyze
        filename = os.path.basename(filepath)

        script = f"""
        tell application "System Events"
            activate
            set dialogResult to display dialog "🆕 Ny fil upptäckt!

{filename}

Vill du att jag analyserar och föreslår var den ska placeras?" buttons {{"Ignorera", "Analysera"}} default button "Analysera" with title "SortMeOut AI" giving up after 30
            return button returned of dialogResult
        end tell
        """

        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)

        if "Analysera" in result.stdout:
            self._analyze_and_suggest(filepath)

    @rumps.clicked("🔄 Organisera Nu")
    def organize_now(self, _):
        """Organize existing files."""
        if not self.api_key:
            self._prompt_api_key()
            return

        rumps.notification(
            title="SortMeOut AI", subtitle="Skannar...", message="Analyserar dina filer..."
        )

        threading.Thread(target=self._bulk_organize, daemon=True).start()

    def _bulk_organize(self):
        """Organize multiple files."""
        folders = self.config.get("folders", ["~/Downloads"])
        files_found = []

        for folder in folders:
            folder_path = os.path.expanduser(folder)
            if os.path.isdir(folder_path):
                for f in os.listdir(folder_path):
                    if not f.startswith("."):
                        filepath = os.path.join(folder_path, f)
                        if os.path.isfile(filepath):
                            files_found.append(filepath)

        if not files_found:
            rumps.notification(
                title="SortMeOut AI", subtitle="Klart", message="Inga filer att organisera."
            )
            return

        # Ask user
        script = f"""
        tell application "System Events"
            activate
            display dialog "Hittade {len(files_found)} filer att analysera.

Vill du gå igenom dem en i taget?" buttons {{"Avbryt", "Starta"}} default button "Starta" with title "SortMeOut AI"
            return button returned of result
        end tell
        """

        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)

        if "Starta" in result.stdout:
            for filepath in files_found[:10]:  # Max 10 at a time
                if not self._quick_analyze(filepath):
                    break

    def _quick_analyze(self, filepath):
        """Quick analyze and suggest for one file."""
        try:
            suggestion = self.assistant.get_suggestion(filepath)
            suggestions = suggestion.get("suggestions", [])

            if not suggestions:
                return True

            filename = os.path.basename(filepath)
            analysis = suggestion.get("analysis", "")[:100]

            buttons = []
            for i, s in enumerate(suggestions[:3]):
                short = os.path.basename(s.get("path", "?").rstrip("/"))
                buttons.append(f"{short}")
            buttons.extend(["Hoppa över", "Stoppa"])

            button_str = '{"' + '", "'.join(reversed(buttons)) + '"}'

            script = f"""
            tell application "System Events"
                activate
                set dialogResult to display dialog "📄 {filename}

{analysis}

Vart ska den flyttas?" buttons {button_str} default button 1 with title "SortMeOut AI"
                return button returned of dialogResult
            end tell
            """

            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            choice = result.stdout.strip()

            if choice == "Stoppa":
                return False
            elif choice == "Hoppa över":
                return True
            else:
                # Find matching suggestion
                for s in suggestions:
                    if os.path.basename(s.get("path", "").rstrip("/")) == choice:
                        self._execute_move(filepath, s["path"])
                        break

            return True

        except Exception as e:
            print(f"Error: {e}")
            return True

    @rumps.clicked("⚙️ Inställningar...")
    def settings(self, _):
        """Open settings."""
        ensure_config()

        # Create config if doesn't exist
        if not os.path.exists(CONFIG_FILE):
            save_config(self.config)

        subprocess.run(["open", "-a", "TextEdit", CONFIG_FILE])

    @rumps.clicked("🔑 API-nyckel...")
    def set_api_key(self, _):
        """Set or update API key."""
        self._prompt_api_key()

    def _prompt_api_key(self):
        """Prompt for API key."""
        current = self.api_key[:20] + "..." if self.api_key else "Ej inställd"

        script = f"""
        tell application "System Events"
            activate
            set keyResult to display dialog "🔑 Claude API-nyckel

Nuvarande: {current}

Klistra in din API-nyckel från console.anthropic.com:" default answer "" buttons {{"Avbryt", "Spara"}} default button "Spara" with title "SortMeOut - API-nyckel" with hidden answer

            if button returned of keyResult is "Spara" then
                return text returned of keyResult
            else
                return ""
            end if
        end tell
        """

        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        new_key = result.stdout.strip()

        if new_key and new_key.startswith("sk-"):
            save_api_key(new_key)
            self.api_key = new_key
            self._init_assistant()

            rumps.notification(
                title="SortMeOut",
                subtitle="API-nyckel sparad",
                message="Din Claude API-nyckel har sparats.",
            )

    @rumps.clicked("📖 Dokumentation")
    def docs(self, _):
        subprocess.run(["open", "https://sortmeout.saidborna.com"])

    @rumps.clicked("ℹ️ Om SortMeOut")
    def about(self, _):
        rumps.alert(
            title="Om SortMeOut AI",
            message="SortMeOut AI v1.1.0\n\nIntelligent filorganisation för macOS.\nPowered by Claude AI.\n\n© 2026 SortMeOut Contributors\nMIT License",
        )

    @rumps.clicked("❌ Avsluta")
    def quit(self, _):
        self.watching = False
        rumps.quit_application()


def main():
    app = SortMeOutAI()
    app.run()


if __name__ == "__main__":
    main()
