"""
AI Personal Assistant powered by Claude API.
Your ultimate macOS companion — files, email, calendar, messages, presentations, and more.
"""

import os
import json
import mimetypes
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime

# License gate import - SINGLE AI GATE
from sortmeout.core.license import (
    can_execute_ai,
    record_ai_execution,
    get_ai_blocked_message,
    get_license,
    LicenseState,
)

# Core engine integration - all AI actions go through HistoryManager
from sortmeout.core.history import get_history

# Integrations — lazy loaded to avoid startup cost
_mail = None
_calendar = None
_messages = None
_contacts = None
_presentations = None
_notes = None


def _get_mail():
    global _mail
    if _mail is None:
        from sortmeout.integrations.mail import MailIntegration

        _mail = MailIntegration()
    return _mail


def _get_calendar():
    global _calendar
    if _calendar is None:
        from sortmeout.integrations.calendar import CalendarIntegration

        _calendar = CalendarIntegration()
    return _calendar


def _get_messages():
    global _messages
    if _messages is None:
        from sortmeout.integrations.messages import MessagesIntegration

        _messages = MessagesIntegration()
    return _messages


def _get_contacts():
    global _contacts
    if _contacts is None:
        from sortmeout.integrations.contacts import ContactsIntegration

        _contacts = ContactsIntegration()
    return _contacts


def _get_presentations():
    global _presentations
    if _presentations is None:
        from sortmeout.integrations.presentations import PresentationBuilder

        _presentations = PresentationBuilder()
    return _presentations


def _get_notes():
    global _notes
    if _notes is None:
        from sortmeout.integrations.notes import NotesIntegration

        _notes = NotesIntegration()
    return _notes


_image_editor = None
_image_generator = None


def _get_image_editor():
    global _image_editor
    if _image_editor is None:
        from sortmeout.integrations.images import get_editor

        _image_editor = get_editor()
    return _image_editor


def _get_image_generator():
    global _image_generator
    if _image_generator is None:
        from sortmeout.integrations.images import get_generator

        _image_generator = get_generator()
    return _image_generator


# Model selection - economical for all users, premium for Creator
MODEL_DEFAULT = "claude-sonnet-4-20250514"  # All users — fast, capable, cost-effective
MODEL_CREATOR = "claude-sonnet-4-5-20250929"  # Creator only — most capable


def get_model() -> str:
    """Get appropriate model based on license state."""
    license = get_license()
    # Only Creator gets the premium model
    if license._pro_license_key and "CREATOR" in license._pro_license_key:
        return MODEL_CREATOR
    return MODEL_DEFAULT  # Everyone else gets the default model


try:
    import anthropic

    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


class FileAssistant:
    """AI-powered file organization assistant using Claude."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the assistant with Claude API."""
        self.api_key = api_key or self._load_api_key()

        if not self.api_key:
            raise ValueError("Claude API key required. Set ANTHROPIC_API_KEY or pass api_key.")

        if not HAS_ANTHROPIC:
            raise ImportError("anthropic package required. Run: pip install anthropic")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.folder_structure = {}
        self.file_history = []
        self.conversation_history = []  # Store conversation history
        self.config_path = os.path.expanduser("~/.config/sortmeout")

        # Load knowledge and persisted conversation
        self._load_folder_structure()
        self._load_history()
        self._load_conversation_history()

    @staticmethod
    def _load_api_key() -> Optional[str]:
        """Load Anthropic API key from .env file, config file, or environment.

        Bundled .app on macOS does NOT inherit shell env vars, so we must
        read from disk first.
        """
        # 1. Try .env file in config directory
        env_file = os.path.expanduser("~/.config/sortmeout/.env")
        if os.path.exists(env_file):
            try:
                with open(env_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("ANTHROPIC_API_KEY="):
                            key = line.split("=", 1)[1].strip()
                            if key:
                                return key
            except Exception:
                pass

        # 2. Try dedicated config file
        config_file = os.path.expanduser("~/Documents/Config/Anthropic/anthropic_api_key.txt")
        if os.path.exists(config_file):
            try:
                with open(config_file, "r") as f:
                    key = f.read().strip()
                    if key:
                        return key
            except Exception:
                pass

        # 3. Fall back to environment variable (works in terminal, not in .app)
        return os.environ.get("ANTHROPIC_API_KEY")

    def _load_folder_structure(self):
        """Scan and learn the user's folder structure."""
        home = os.path.expanduser("~")
        important_dirs = [
            "Documents",
            "Downloads",
            "Desktop",
            "Pictures",
            "Movies",
            "Music",
            "Developer",
            "Projects",
            "School",
        ]

        structure = {}
        for dirname in important_dirs:
            dirpath = os.path.join(home, dirname)
            if os.path.isdir(dirpath):
                structure[dirname] = self._scan_directory(dirpath, max_depth=2)

        self.folder_structure = structure

        # Save structure for reference
        os.makedirs(self.config_path, exist_ok=True)
        structure_file = os.path.join(self.config_path, "folder_structure.json")
        try:
            with open(structure_file, "w") as f:
                json.dump(structure, f, indent=2)
        except:
            pass

    def _scan_directory(self, path: str, max_depth: int = 2, current_depth: int = 0) -> Dict:
        """Recursively scan directory structure."""
        if current_depth >= max_depth:
            return {"_type": "folder"}

        result = {"_type": "folder", "_subfolders": [], "_files": []}

        try:
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                if item.startswith("."):
                    continue
                if os.path.isdir(item_path):
                    result["_subfolders"].append(item)
                    if current_depth < max_depth - 1:
                        result[item] = self._scan_directory(item_path, max_depth, current_depth + 1)
                else:
                    # Include files too (max 50 per folder to avoid overload)
                    if len(result["_files"]) < 50:
                        result["_files"].append(item)
        except PermissionError:
            pass

        return result

    def list_files_in_folder(self, folder_path: str) -> List[Dict]:
        """List all files in a folder with details."""
        folder = Path(os.path.expanduser(folder_path))
        if not folder.exists():
            return []

        files = []
        try:
            for item in folder.iterdir():
                if item.name.startswith("."):
                    continue
                info = {
                    "name": item.name,
                    "is_dir": item.is_dir(),
                    "extension": item.suffix.lower() if not item.is_dir() else "",
                    "size": item.stat().st_size if not item.is_dir() else 0,
                }
                files.append(info)
        except PermissionError:
            pass

        return sorted(files, key=lambda x: (not x["is_dir"], x["name"].lower()))

    def _load_history(self):
        """Load file organization history."""
        history_file = os.path.join(self.config_path, "history.json")
        if os.path.exists(history_file):
            try:
                with open(history_file, "r") as f:
                    self.file_history = json.load(f)
            except:
                self.file_history = []

    def _load_conversation_history(self):
        """Load persisted conversation history from disk."""
        chat_file = os.path.join(self.config_path, "chat_history.json")
        if os.path.exists(chat_file):
            try:
                with open(chat_file, "r") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    # Keep last 20 messages
                    self.conversation_history = data[-20:]
            except Exception:
                self.conversation_history = []

    def _save_conversation_history(self):
        """Persist conversation history to disk."""
        chat_file = os.path.join(self.config_path, "chat_history.json")
        try:
            os.makedirs(self.config_path, exist_ok=True)
            with open(chat_file, "w") as f:
                json.dump(self.conversation_history[-20:], f, indent=2, ensure_ascii=False)
        except Exception:
            pass  # Don't let history persistence break the flow

    def _save_history(self, entry: Dict):
        """Save a history entry to core engine's SQLite database.

        Routes through HistoryManager so AI actions appear in
        `sortmeout history`, are undoable, and included in statistics.
        """
        action_type = entry.get("action", "unknown")
        source = entry.get("source", entry.get("filename", ""))
        destination = entry.get("destination", "")

        try:
            get_history().record(
                action_type=action_type,
                source_path=source,
                destination_path=destination,
                success=True,
                rule_name="AI Assistant",
                metadata={"via": "ai_chat", "timestamp": entry.get("timestamp", "")},
            )
        except Exception:
            pass  # Don't let history failures break the AI flow

        # Also keep local cache for session context
        self.file_history.append(entry)
        self.file_history = self.file_history[-100:]

    def analyze_file(self, filepath: str) -> Dict[str, Any]:
        """Analyze a file and extract information."""
        path = Path(filepath)

        if not path.exists():
            return {"error": f"File not found: {filepath}"}

        info = {
            "name": path.name,
            "extension": path.suffix.lower(),
            "size": path.stat().st_size,
            "size_human": self._human_size(path.stat().st_size),
            "created": datetime.fromtimestamp(path.stat().st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
            "mime_type": mimetypes.guess_type(str(path))[0],
            "is_directory": path.is_dir(),
            "parent": str(path.parent),
        }

        # Try to read content for text files
        content_preview = None
        if not path.is_dir() and info["size"] < 1_000_000:  # < 1MB
            text_extensions = [
                ".txt",
                ".md",
                ".py",
                ".js",
                ".json",
                ".csv",
                ".html",
                ".xml",
                ".yaml",
                ".yml",
            ]
            if info["extension"] in text_extensions:
                try:
                    with open(path, "r", encoding="utf-8", errors="ignore") as f:
                        content_preview = f.read(2000)  # First 2000 chars
                except:
                    pass

        info["content_preview"] = content_preview
        return info

    def _human_size(self, size: int) -> str:
        """Convert bytes to human readable size."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def get_suggestion(self, filepath: str, user_context: str = "") -> Dict[str, Any]:
        """Get AI suggestion for what to do with a file."""
        # SINGLE AI GATE - hard stop if not allowed
        allowed, message = can_execute_ai()
        if not allowed:
            return {"error": "license_required", "message": message}

        file_info = self.analyze_file(filepath)

        if "error" in file_info:
            return file_info

        # Build context about folder structure
        folder_context = json.dumps(self.folder_structure, indent=2)

        # Build recent history context
        recent_history = self.file_history[-10:] if self.file_history else []
        history_context = "\n".join(
            [
                f"- {h.get('filename', 'unknown')} → {h.get('destination', 'unknown')}"
                for h in recent_history
            ]
        )

        prompt = f"""You are an intelligent file assistant for macOS. The user has a new file and needs help organizing it.

FILE INFORMATION:
- Name: {file_info['name']}
- Type: {file_info['extension']} ({file_info['mime_type']})
- Size: {file_info['size_human']}
- Current location: {file_info['parent']}

{f"FILE CONTENT (preview):{chr(10)}{file_info['content_preview'][:500]}" if file_info.get('content_preview') else ""}

USER'S FOLDER STRUCTURE:
{folder_context}

PREVIOUS ORGANIZATION (for context):
{history_context if history_context else "No history yet"}

{f"USER'S COMMENT: {user_context}" if user_context else ""}

TASK:
1. Analyze the file based on name, type, and content
2. Suggest 3-4 suitable locations based on the user's folder structure
3. Give a recommendation and explain why

Respond in English in this JSON format:
{{
  "analysis": "Brief analysis of what the file appears to be",
  "suggestions": [
    {{"path": "~/Documents/...", "reason": "Why this location is suitable", "confidence": 0.9}},
    {{"path": "~/...", "reason": "...", "confidence": 0.7}}
  ],
  "recommended": 0,
  "additional_actions": ["Rename to...", "Create subfolder...", etc],
  "question": "Optional follow-up question for the user"
}}"""

        try:
            response = self.client.messages.create(
                model=get_model(),
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}],
            )

            # Record successful AI execution for rate limiting
            record_ai_execution()

            # Parse response
            response_text = response.content[0].text

            # Try to extract JSON
            import re

            json_match = re.search(r"\{[\s\S]*\}", response_text)
            if json_match:
                suggestion = json.loads(json_match.group())
                suggestion["file_info"] = file_info
                return suggestion
            else:
                return {"analysis": response_text, "suggestions": [], "file_info": file_info}

        except Exception as e:
            return {"error": f"AI error: {str(e)}", "file_info": file_info}

    def execute_action(self, filepath: str, action: str, destination: str = None, **kwargs) -> Dict:
        """Execute an action on a file."""
        import shutil

        path = Path(filepath)
        if not path.exists():
            return {"success": False, "error": "File not found"}

        result = {"success": False, "action": action}

        try:
            if action == "move":
                if not destination:
                    return {"success": False, "error": "Destination required"}

                dest_path = Path(os.path.expanduser(destination))
                dest_path.mkdir(parents=True, exist_ok=True)

                final_dest = dest_path / path.name

                # Handle duplicates
                if final_dest.exists():
                    base = path.stem
                    ext = path.suffix
                    counter = 1
                    while final_dest.exists():
                        final_dest = dest_path / f"{base} ({counter}){ext}"
                        counter += 1

                shutil.move(str(path), str(final_dest))
                result = {"success": True, "action": "move", "destination": str(final_dest)}
                get_history().record(
                    action_type="move",
                    source_path=str(path),
                    destination_path=str(final_dest),
                    rule_name="AI Assistant",
                    metadata={"via": "ai_execute_action"},
                )

            elif action == "copy":
                if not destination:
                    return {"success": False, "error": "Destination required"}

                dest_path = Path(os.path.expanduser(destination))
                dest_path.mkdir(parents=True, exist_ok=True)

                final_dest = dest_path / path.name
                shutil.copy2(str(path), str(final_dest))
                result = {"success": True, "action": "copy", "destination": str(final_dest)}
                get_history().record(
                    action_type="copy",
                    source_path=str(path),
                    destination_path=str(final_dest),
                    rule_name="AI Assistant",
                    metadata={"via": "ai_execute_action"},
                )

            elif action == "rename":
                new_name = kwargs.get("new_name")
                if not new_name:
                    return {"success": False, "error": "New name required"}

                new_path = path.parent / new_name
                path.rename(new_path)
                result = {"success": True, "action": "rename", "new_path": str(new_path)}
                get_history().record(
                    action_type="rename",
                    source_path=str(path),
                    destination_path=str(new_path),
                    rule_name="AI Assistant",
                    metadata={"via": "ai_execute_action"},
                )

            elif action == "trash":
                import subprocess

                subprocess.run(
                    [
                        "osascript",
                        "-e",
                        f'tell application "Finder" to delete POSIX file "{filepath}"',
                    ],
                    check=True,
                )
                result = {"success": True, "action": "trash"}
                get_history().record(
                    action_type="trash",
                    source_path=str(path),
                    rule_name="AI Assistant",
                    metadata={"via": "ai_execute_action"},
                )

            elif action == "open":
                import subprocess

                subprocess.run(["open", filepath])
                result = {"success": True, "action": "open"}

            # Save to history (already recorded via get_history().record() above)
            if result.get("success"):
                self._save_history(
                    {
                        "filename": path.name,
                        "action": action,
                        "source": str(path),
                        "destination": destination,
                        "timestamp": datetime.now().isoformat(),
                    }
                )

        except Exception as e:
            result = {"success": False, "error": str(e)}

        return result

    # ── Live context gathering for integrations ──

    def _gather_live_context(self, message: str) -> str:
        """Gather live context from integrations based on user message keywords.

        Returns a string with relevant context to prepend to the system prompt,
        so the AI can proactively reference the user's mail, calendar, etc.
        """
        parts: list[str] = []
        msg_lower = message.lower()

        # Keywords that trigger each integration
        mail_keywords = {
            "mail",
            "email",
            "inbox",
            "unread",
            "message from",
            "reply to",
            "send email",
            "e-post",
            "mejl",
        }
        cal_keywords = {
            "calendar",
            "event",
            "meeting",
            "deadline",
            "schedule",
            "today",
            "tomorrow",
            "week",
            "kalender",
            "möte",
            "dag",
            "briefing",
            "how's my day",
            "hows my day",
        }
        msg_keywords = {
            "imessage",
            "sms",
            "text message",
            "message",
            "meddelande",
            "skicka",
            "send message",
        }
        contact_keywords = {"contact", "phone number", "email address", "kontakt", "telefon"}
        notes_keywords = {"note", "notes", "anteckning", "anteckningar"}
        daily_keywords = {
            "how's my day",
            "hows my day",
            "daily briefing",
            "morning",
            "what's up",
            "overview",
            "summary",
            "sammanfattning",
            "hur ser min dag ut",
            "god morgon",
            "good morning",
        }

        # Daily briefing — gather everything
        if any(kw in msg_lower for kw in daily_keywords):
            try:
                cal = _get_calendar()
                briefing = cal.get_daily_briefing()
                parts.append(f"\n📅 CALENDAR BRIEFING:\n{briefing}")
            except Exception as e:
                parts.append(f"\n📅 Calendar unavailable: {e}")

            try:
                mail = _get_mail()
                summary = mail.get_summary()
                parts.append(f"\n📧 MAIL SUMMARY:\n{summary}")
            except Exception as e:
                parts.append(f"\n📧 Mail unavailable: {e}")

            try:
                msgs = _get_messages()
                summary = msgs.get_summary()
                parts.append(f"\n💬 MESSAGES SUMMARY:\n{summary}")
            except Exception as e:
                pass  # Messages less critical

        else:
            # Individual context gathering
            if any(kw in msg_lower for kw in mail_keywords):
                try:
                    mail = _get_mail()
                    count = mail.get_unread_count()
                    parts.append(f"\n📧 MAIL CONTEXT: {count} unread email(s)")
                    if count > 0:
                        recent = mail.get_recent_emails(3, unread_only=True)
                        if recent:
                            parts.append("Recent unread:")
                            for e in recent[:3]:
                                parts.append(
                                    f"  - From: {e.get('sender', '?')} | Subject: {e.get('subject', '?')}"
                                )
                except Exception:
                    pass

            if any(kw in msg_lower for kw in cal_keywords):
                try:
                    cal = _get_calendar()
                    events = cal.get_events_today()
                    parts.append(f"\n📅 CALENDAR CONTEXT: {len(events)} event(s) today")
                    for ev in events[:5]:
                        parts.append(f"  - {ev.get('title', '?')} at {ev.get('start_time', '?')}")
                except Exception:
                    pass

            if any(kw in msg_lower for kw in msg_keywords):
                try:
                    msgs = _get_messages()
                    chats = msgs.get_recent_chats(3)
                    if chats:
                        parts.append(f"\n💬 RECENT MESSAGES:")
                        for c in chats[:3]:
                            parts.append(
                                f"  - {c.get('name', '?')}: {c.get('last_message', '?')[:60]}"
                            )
                except Exception:
                    pass

            if any(kw in msg_lower for kw in notes_keywords):
                try:
                    notes = _get_notes()
                    recent = notes.get_recent_notes(3)
                    if recent:
                        parts.append(f"\n📝 RECENT NOTES:")
                        for n in recent[:3]:
                            parts.append(f"  - {n.get('name', '?')}")
                except Exception:
                    pass

        if parts:
            return "\n\n── LIVE CONTEXT ──" + "\n".join(parts) + "\n── END LIVE CONTEXT ──\n"
        return ""

    def chat(self, message: str, files: List[str] = None) -> str:
        """General chat with the assistant. Maintains conversation history."""

        # SINGLE AI GATE - hard stop if not allowed
        allowed, blocked_message = can_execute_ai()
        if not allowed:
            return blocked_message

        # Check if user is confirming pending commands
        if (
            self._user_has_confirmed(message)
            and hasattr(self, "pending_commands")
            and self.pending_commands
        ):
            num_commands = len(self.pending_commands)
            result = self._execute_pending_commands()
            self.pending_commands = []
            return f"🚀 **Executing {num_commands} action(s)...**{result}"

        files_context = ""
        if files:
            for f in files:
                info = self.analyze_file(f)
                files_context += f"\nFile: {info.get('name', f)}\n"
                files_context += f"  Type: {info.get('extension', 'unknown')}\n"
                files_context += f"  Size: {info.get('size_human', 'unknown')}\n"

        folder_context = json.dumps(self.folder_structure, indent=2)
        home_dir = os.path.expanduser("~")

        # Get detailed list of Downloads files
        downloads_files = self.list_files_in_folder("~/Downloads")
        downloads_list = ""
        if downloads_files:
            downloads_list = "\n\nFILES IN DOWNLOADS:\n"
            for f in downloads_files:
                ftype = "📁" if f["is_dir"] else "📄"
                downloads_list += f"  {ftype} {f['name']}\n"
        else:
            downloads_list = "\n\nDOWNLOADS: (empty)\n"

        # ── Gather live context from integrations ──
        live_context = self._gather_live_context(message)
        system_prompt = f"""You are SortMeOut Assistant, the user's ultimate personal AI for macOS.
You are NOT just a file organizer — you are a full personal assistant with access to:
- Files & folders (organize, move, search, compress, tag)
- Email (read, compose, reply, search via Mail.app)
- Calendar (events, deadlines, scheduling via Calendar.app)
- Messages (read & send iMessages)
- Contacts (search & lookup)
- Presentations (create PowerPoint/Keynote)
- Notes (read, create, search Apple Notes)
- Images (CREATE with DALL-E 3, edit, resize, crop, filter, convert, compress)
- System control (volume, dark mode, screenshots, disk space, battery, etc.)

YOU CAN CREATE IMAGES! Logos, graphics, art, photos — anything visual.
Use [EXECUTE: img_generate "prompt" "options"] to create images from text descriptions.
NEVER say you cannot create images. You HAVE this ability via DALL-E 3.

PERSONALITY:
- Be warm, helpful, and proactive
- Anticipate what the user might need next
- When asked "how's my day?" — check calendar, mail, deadlines automatically
- Show off your full capabilities when relevant
- Be careful with destructive actions — always confirm first

CRITICAL RULE — READ CAREFULLY:
You must NEVER include [EXECUTE:...] commands in a response where you also ask a question!
- If you present a plan and ask "Would you like me to do this?" = NO EXECUTE commands
- ONLY when the user has ALREADY replied "yes", "go ahead", "do it" = then you may use EXECUTE

WORKFLOW (follow exactly):
STEP 1 - First response:
- Present a detailed plan
- List each action clearly
- End with: "Would you like me to proceed? (yes/no)"
- NO [EXECUTE:] COMMANDS IN THIS RESPONSE!

STEP 2 - After the user says yes:
- Now and ONLY now may you use [EXECUTE:] commands
- Execute all actions
- Include a SUMMARY section showing every action

═══════════════════════════════════════════════════
EXECUTE COMMANDS — YOUR FULL TOOLKIT
═══════════════════════════════════════════════════

📁 FILE MANAGEMENT:
[EXECUTE: mkdir "{home_dir}/Desktop/NewFolder"]
[EXECUTE: move "{home_dir}/Downloads/file.pdf" "{home_dir}/Documents/"]
[EXECUTE: copy "{home_dir}/Downloads/file.pdf" "{home_dir}/Desktop/Backup/"]
[EXECUTE: rename "{home_dir}/Desktop/old_name.txt" "new_name.txt"]
[EXECUTE: trash "{home_dir}/Desktop/unwanted_file.txt"]
[EXECUTE: symlink "{home_dir}/Documents/original" "{home_dir}/Desktop/shortcut"]

🔍 SEARCH & INFO:
[EXECUTE: search "budget report 2024"]
[EXECUTE: getinfo "{home_dir}/Documents/file.pdf"]
[EXECUTE: foldersize "{home_dir}/Downloads"]

🏷️ FINDER TAGS:
[EXECUTE: tag "{home_dir}/Documents/report.pdf" "Important"]
[EXECUTE: untag "{home_dir}/Documents/report.pdf" "Old"]

📂 OPEN & REVEAL:
[EXECUTE: open "{home_dir}/Documents/file.pdf"]
[EXECUTE: openapp "Safari"]
[EXECUTE: reveal "{home_dir}/Documents/project/"]
[EXECUTE: preview "{home_dir}/Pictures/photo.jpg"]

🗜️ COMPRESSION:
[EXECUTE: compress "{home_dir}/Documents/project_folder"]
[EXECUTE: decompress "{home_dir}/Downloads/archive.zip"]

🗑️ TRASH:
[EXECUTE: emptytrash ""]

📋 CLIPBOARD:
[EXECUTE: clipboard "Text to copy to clipboard"]

📸 SCREENSHOT:
[EXECUTE: screenshot ""]

🔔 NOTIFICATIONS:
[EXECUTE: notify "Title" "Your task is complete!"]

🗣️ TEXT TO SPEECH:
[EXECUTE: say "Hello, your files are organized!"]

🌓 APPEARANCE:
[EXECUTE: darkmode ""]
[EXECUTE: wallpaper "{home_dir}/Pictures/wallpaper.jpg"]
[EXECUTE: hiddenfiles ""]

🔊 AUDIO:
[EXECUTE: volume "50"]
[EXECUTE: mute ""]

💻 SYSTEM INFO:
[EXECUTE: diskspace ""]
[EXECUTE: battery ""]
[EXECUTE: wifi ""]
[EXECUTE: runningapps ""]

⚙️ SYSTEM ACTIONS:
[EXECUTE: killprocess "ProcessName"]
[EXECUTE: eject "USB Drive"]
[EXECUTE: lockscreen ""]

═══════════════════════════════════════════════════
📧 EMAIL (Mail.app)
═══════════════════════════════════════════════════

[EXECUTE: mail_unread ""]
  → Get unread email count

[EXECUTE: mail_recent "5"]
  → Get 5 most recent emails (subject, sender, date, preview)

[EXECUTE: mail_read "MESSAGE_ID"]
  → Read full email content by ID

[EXECUTE: mail_search "invoice"]
  → Search emails by keyword

[EXECUTE: mail_search_all "invoice"]
  → Search emails across ALL mailboxes (Inbox, Sent, Archive, Drafts)

[EXECUTE: mail_compose "to@example.com" "Subject|Body text here"]
  → Compose and open as draft (pipe separates subject and body)

[EXECUTE: mail_send "to@example.com" "Subject|Body text here"]
  → Compose and SEND immediately

[EXECUTE: mail_compose "to@example.com" "Subject|Body text|/path/to/file.pdf"]
  → Compose with ATTACHMENT (subject|body|attachment_path)

[EXECUTE: mail_reply "MESSAGE_ID" "Reply body text"]
  → Reply to an email (opens as draft)

[EXECUTE: mail_reply_send "MESSAGE_ID" "Reply body text"]
  → Reply and SEND immediately

[EXECUTE: mail_flag "MESSAGE_ID"]
  → Flag an email

[EXECUTE: mail_markread "MESSAGE_ID"]
  → Mark email as read

═══════════════════════════════════════════════════
📅 CALENDAR (Calendar.app)
═══════════════════════════════════════════════════

[EXECUTE: cal_today ""]
  → Get today's events

[EXECUTE: cal_tomorrow ""]
  → Get tomorrow's events

[EXECUTE: cal_week ""]
  → Get this week's events

[EXECUTE: cal_upcoming "14"]
  → Get events for the next 14 days

[EXECUTE: cal_search "meeting"]
  → Search events by keyword

[EXECUTE: cal_deadlines ""]
  → Find upcoming deadlines (exams, due dates, submissions)

[EXECUTE: cal_create "Meeting Title" "2026-02-10T14:00|2026-02-10T15:00|Office|Discussion notes"]
  → Create event (start|end|location|notes — end/location/notes optional)

[EXECUTE: cal_edit "Meeting Title" "new_title|new_start|new_end|new_location|new_notes"]
  → Edit existing event (any field can be empty to keep unchanged)
  Example: [EXECUTE: cal_edit "Old Title" "New Title|||New Location|"]

[EXECUTE: cal_delete "Meeting Title"]
  → Delete a calendar event by title

[EXECUTE: cal_briefing ""]
  → Full daily briefing (today's events, tomorrow preview, deadlines)

═══════════════════════════════════════════════════
💬 MESSAGES (iMessage)
═══════════════════════════════════════════════════

[EXECUTE: msg_chats ""]
  → List recent conversations

[EXECUTE: msg_send "+46701234567" "Message text"]
  → Send an iMessage to a phone number or email

[EXECUTE: msg_read "+46701234567" "10"]
  → Read last 10 messages from a contact (phone/email)
  Shows message text, sender, and timestamp

═══════════════════════════════════════════════════
👤 CONTACTS
═══════════════════════════════════════════════════

[EXECUTE: contact_search "John"]
  → Search contacts by name, email, or phone

[EXECUTE: contact_groups ""]
  → List contact groups

[EXECUTE: contact_create "John|Doe|+46701234567|john@email.com|Company AB|Notes"]
  → Create new contact (first|last|phone|email|org|note — only first name required)

[EXECUTE: contact_edit "John Doe" "new_phone|new_email|new_org|new_note"]
  → Edit existing contact (any field can be empty to skip)

[EXECUTE: contact_delete "John Doe"]
  → Delete a contact by name

═══════════════════════════════════════════════════
📊 PRESENTATIONS
═══════════════════════════════════════════════════

[EXECUTE: pres_create "Presentation Title" "OUTLINE"]
  → Create a presentation from markdown outline
  The outline format (use \\n for newlines):
    # Title\\n## Slide 1\\n- Point A\\n- Point B\\n## Slide 2\\n- Point C

═══════════════════════════════════════════════════
📝 NOTES (Apple Notes)
═══════════════════════════════════════════════════

[EXECUTE: notes_recent "5"]
  → Get 5 most recent notes

[EXECUTE: notes_read "Note Title"]
  → Read a note's full content

[EXECUTE: notes_create "Title" "Body content"]
  → Create a new note

[EXECUTE: notes_search "keyword"]
  → Search notes

[EXECUTE: notes_append "Note Title" "Text to add"]
  → Append text to existing note

[EXECUTE: notes_edit "Note Title" "New full body content"]
  → Replace note body with new content

[EXECUTE: notes_delete "Note Title"]
  → Delete a note by title

═══════════════════════════════════════════════════
🎨 IMAGES (Create & Edit)
═══════════════════════════════════════════════════

🤖 AI IMAGE GENERATION (DALL-E 3 — high quality):
[EXECUTE: img_generate "A futuristic city at sunset with flying cars, photorealistic" "1024x1024|hd|vivid"]
  → Generate image from text (size|quality|style — all optional)
  Sizes: 1024x1024 (square), 1024x1792 (portrait), 1792x1024 (landscape)
  Quality: hd (default, detailed) or standard
  Style: vivid (dramatic, default) or natural (realistic)
  TIP: Be VERY detailed in prompts for best results!

[EXECUTE: img_edit_ai "/path/to/image.png" "Add a rainbow in the sky"]
  → AI-edit an existing image with a text prompt

✂️ IMAGE EDITING (local, instant):
[EXECUTE: img_resize "/path/to/image.png" "800|0"]
  → Resize (width|height — 0 = auto-calculate to keep aspect ratio)

[EXECUTE: img_crop "/path/to/image.png" "100|100|800|600"]
  → Crop to box (left|top|right|bottom)

[EXECUTE: img_rotate "/path/to/image.png" "90"]
  → Rotate counter-clockwise by degrees

[EXECUTE: img_flip "/path/to/image.png" "horizontal"]
  → Flip horizontally or vertically

[EXECUTE: img_filter "/path/to/image.png" "grayscale|1.0"]
  → Apply filter (name|intensity)
  Filters: blur, sharpen, detail, edge_enhance, emboss, contour, smooth,
           grayscale, sepia, invert, brightness, contrast, saturation,
           auto_contrast, equalize

[EXECUTE: img_text "/path/to/image.png" "© SortMeOut 2026|bottom-right|30|white"]
  → Add text overlay (text|position|font_size|color)
  Positions: top-left, top-right, bottom-left, bottom-right, center

[EXECUTE: img_convert "/path/to/image.png" "webp|90"]
  → Convert format (format|quality)
  Formats: png, jpeg, webp, tiff, bmp, gif

[EXECUTE: img_compress "/path/to/image.png" "70|1200"]
  → Compress image (quality|max_width — max_width 0 = no resize)

[EXECUTE: img_info "/path/to/image.png" ""]
  → Get image details (dimensions, format, size, color mode)

═══════════════════════════════════════════════════
📐 RULE CREATION (persistent automation)
═══════════════════════════════════════════════════

[EXECUTE: createrule "Rule Name" "folder|attribute|operator|value|action_type|action_arg"]
[EXECUTE: renameai "Jarvis"]

═══════════════════════════════════════════════════

IMPORTANT RULES FOR EXECUTE:
- NEVER use wildcards (*) — they don't work
- ALWAYS use exact filenames
- One EXECUTE per action
- Always use full paths (starting with {home_dir})
- Commands with no argument still need empty quotes: [EXECUTE: battery ""]
- Write ALL commands in ONE response after confirmation
- Write ALL mkdir commands first, then other actions

PROACTIVE INTELLIGENCE:
When the user says things like:
- "How's my day?" → run cal_briefing + mail_unread + deadlines
- "What did I miss?" → check unread mail + recent messages
- "Help me prepare for my meeting" → check calendar, find related files, offer to create presentation
- "Clean up Downloads" → analyze files, suggest organization
- "Email Jan about the project" → find Jan in contacts, compose email
- "Remind me about X" → create calendar event or note
- "What's my schedule?" → show today + tomorrow events
- "Any urgent emails?" → check unread, highlight urgent keywords

SCOPE — WHAT YOU CAN DO:
You are a POWERFUL assistant. Here is your COMPLETE capability list — NEVER deny having any of these:

📁 FILES & FOLDERS:
- Move, copy, rename, delete (trash) files and folders
- Create folders (mkdir), create symlinks
- Search files by name across the entire Mac (Spotlight)
- Get file info (size, dates, type, permissions)
- Calculate folder sizes
- Compress files/folders to ZIP
- Decompress/extract archives
- Empty the Trash
- Open files in their default app
- Open any app by name
- Reveal files in Finder
- Preview files with Quick Look
- Show/hide hidden files

🏷️ ORGANIZATION:
- Add/remove Finder color tags (Red, Orange, Yellow, Green, Blue, Purple, Gray)
- Create automated sorting rules (persistent, run on schedule)
- Rename the AI assistant

📋 PRODUCTIVITY:
- Copy text to clipboard
- Take screenshots
- Send desktop notifications
- Text-to-speech (read text aloud)

📧 EMAIL (Mail.app):
- Check unread email count
- Read recent emails (subject, sender, date, preview, full body)
- Search emails by keyword (inbox only or across ALL mailboxes incl. Sent, Archive)
- Compose email drafts (with optional file attachments)
- Send emails directly (with optional file attachments)
- Reply to emails (draft or send)
- Flag emails
- Mark emails as read

📅 CALENDAR (Calendar.app):
- View today's, tomorrow's, this week's events
- View upcoming events for any number of days
- Search events by keyword
- Find deadlines (exams, due dates, submissions)
- Create new calendar events with title, time, location, notes
- **Edit existing events** (change title, time, location, notes)
- **Delete events**
- Get daily briefing (today + tomorrow + deadlines combined)

💬 MESSAGES (iMessage):
- List recent iMessage conversations
- **Read message history** from any contact (text, sender, timestamps)
- Send iMessages to any phone number or email

👤 CONTACTS:
- Search contacts by name, phone, or email
- List contact groups
- **Create new contacts** (name, phone, email, organization, notes)
- **Edit existing contacts** (add phone, email, change org/notes)
- **Delete contacts**

📊 PRESENTATIONS:
- Create PowerPoint/Keynote presentations from text outlines
- Generate slide content with professional formatting

📝 NOTES (Apple Notes):
- List recent notes
- Read full note content
- Create new notes
- Search notes by keyword
- Append text to existing notes
- **Edit/replace note content**
- **Delete notes**

🎨 IMAGES — YOU CAN CREATE AND EDIT IMAGES:
- **GENERATE images from text descriptions** using DALL-E 3 (logos, art, photos, graphics, concept art, illustrations — ANYTHING visual)
- AI-edit existing images with text prompts
- Resize images (with aspect ratio preservation)
- Crop images to specific dimensions
- Rotate images any number of degrees
- Flip images horizontally or vertically
- Apply 15+ filters: blur, sharpen, detail, edge enhance, emboss, contour, smooth, grayscale, sepia, invert, brightness, contrast, saturation, auto contrast, equalize
- Add text overlays and watermarks (custom font, size, color, position)
- Convert between formats: PNG, JPEG, WEBP, TIFF, BMP, GIF
- Compress images to reduce file size
- Get image info (dimensions, format, file size, color mode)

💻 SYSTEM CONTROL:
- Toggle Dark Mode
- Set wallpaper
- Adjust volume (0-100)
- Mute/unmute
- Check disk space
- Check battery status
- Check WiFi info
- List running applications
- Kill/quit processes
- Eject external drives
- Lock screen

🧠 PROACTIVE INTELLIGENCE:
- Daily briefing combining calendar + email + deadlines
- Suggest file organization based on patterns
- Cross-reference contacts with emails
- Create meeting agendas from calendar events
- Summarize email threads
- Plan your day based on schedule + deadlines
- Learn user patterns and preferences over time

SCOPE — WHAT YOU CANNOT DO (be honest):
- Browse the internet or download files from the web
- Install software or system updates
- Access cloud services directly (Google Drive, Dropbox, iCloud Drive files)
- Modify system security settings or passwords
- Access other users' accounts
NOTE: You CAN create images, logos, art, and graphics! NEVER list image creation as something you cannot do.
If asked about something you can't do, politely explain what you CAN do instead and suggest alternatives.

USER'S HOME DIRECTORY: {home_dir}

USER'S FOLDER STRUCTURE:
{folder_context}
{downloads_list}

{f"FILES BEING DISCUSSED:{files_context}" if files_context else ""}

{live_context}

IMPORTANT:
- ALWAYS reference exact filenames from the list above
- Create folders with mkdir BEFORE moving files to them
- Always respond in the same language as the user
- Be transparent about what you plan to do
- When in doubt — ask the user!"""

        # Add the user's message to history
        self.conversation_history.append({"role": "user", "content": message})

        # Limit history to last 20 messages
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]

        # Persist to disk
        self._save_conversation_history()

        try:
            response = self.client.messages.create(
                model=get_model(),
                max_tokens=8000,  # High limit to run all commands in one pass
                system=system_prompt,
                messages=self.conversation_history,
            )

            # Record successful AI execution for rate limiting
            record_ai_execution()

            assistant_response = response.content[0].text

            # Save assistant's response to history
            self.conversation_history.append({"role": "assistant", "content": assistant_response})
            self._save_conversation_history()

            # SAFETY CHECK: Do NOT run commands if the AI is asking for confirmation
            if self._is_asking_for_confirmation(assistant_response):
                # Store commands for later, but don't run them now
                self.pending_commands = self._extract_commands(assistant_response)
                # Remove EXECUTE commands from the response so they aren't displayed
                clean_response = self._remove_execute_commands(assistant_response)
                if self.pending_commands:
                    clean_response += (
                        f"\n\n*({len(self.pending_commands)} action(s) awaiting confirmation)*"
                    )
                return clean_response

            # Execute any commands in the response (if no question is asked)
            executed_response = self._execute_commands_in_response(assistant_response)

            return executed_response

        except Exception as e:
            return f"Error communicating with AI: {str(e)}"

    def _is_asking_for_confirmation(self, response: str) -> bool:
        """Detect if the AI is asking the user for confirmation."""
        confirmation_phrases = [
            "would you like me to",
            "shall i proceed",
            "(yes/no)",
            "yes or no",
            "confirm",
            "should i execute",
            "should i go ahead",
            "do you approve",
            "would you like to proceed",
            "want me to continue",
        ]
        response_lower = response.lower()
        return any(phrase in response_lower for phrase in confirmation_phrases)

    def _user_has_confirmed(self, message: str) -> bool:
        """Check if the user's message is a confirmation."""
        confirmations = [
            "yes",
            "yeah",
            "yep",
            "yup",
            "sure",
            "ok",
            "okay",
            "go ahead",
            "do it",
            "proceed",
            "continue",
            "absolutely",
            "go for it",
            "ja",
            "kör",
        ]
        message_lower = message.lower().strip()
        return message_lower in confirmations or message_lower.startswith("yes ")

    # ──────────────────────────────────────────────────────────────
    # ALL KNOWN COMMANDS — single source of truth for regex
    # ──────────────────────────────────────────────────────────────
    _ALL_COMMANDS = (
        # Files
        "move|copy|rename|mkdir|trash|open|openapp|search|tag|untag|reveal|"
        "compress|decompress|getinfo|emptytrash|notify|clipboard|screenshot|"
        "darkmode|volume|preview|killprocess|diskspace|battery|wifi|lockscreen|"
        "say|eject|symlink|wallpaper|hiddenfiles|runningapps|foldersize|mute|"
        "createrule|renameai|"
        # Mail
        "mail_unread|mail_recent|mail_read|mail_search|mail_search_all|mail_compose|mail_send|"
        "mail_reply|mail_reply_send|mail_flag|mail_markread|"
        # Calendar
        "cal_today|cal_tomorrow|cal_week|cal_upcoming|cal_search|cal_deadlines|"
        "cal_create|cal_briefing|cal_edit|cal_delete|"
        # Messages
        "msg_chats|msg_send|msg_read|"
        # Contacts
        "contact_search|contact_groups|contact_create|contact_edit|contact_delete|"
        # Presentations
        "pres_create|"
        # Notes
        "notes_recent|notes_read|notes_create|notes_search|notes_append|"
        "notes_edit|notes_delete|"
        # Images
        "img_generate|img_edit_ai|img_resize|img_crop|img_rotate|img_flip|"
        "img_filter|img_text|img_convert|img_compress|img_info"
    )

    @property
    def _command_pattern(self) -> str:
        return rf'\[EXECUTE:\s*({self._ALL_COMMANDS})\s*(?:"([^"]*)")?(?:\s+"([^"]*)")?\]'

    def _extract_commands(self, response: str) -> list:
        """Extract EXECUTE commands from the response without running them."""
        import re

        return re.findall(self._command_pattern, response)

    def _remove_execute_commands(self, response: str) -> str:
        """Remove EXECUTE commands from the AI response."""
        import re

        clean = re.sub(self._command_pattern, "", response)
        # Remove extra blank lines
        clean = re.sub(r"\n{3,}", "\n\n", clean)
        return clean.strip()

    def _create_rule_from_chat(self, rule_name: str, rule_spec: str) -> str:
        """Create a persistent rule from the AI chat.

        rule_spec format: "folder|attribute|operator|value|action_type|action_arg"
        Examples:
            "~/Downloads|extension|equals|pdf|move|~/Documents/PDFs"
            "~/Desktop|size|greater_than|100MB|trash|"
            "~/Downloads|name|contains|screenshot|move|~/Pictures/Screenshots"
        """
        try:
            from sortmeout.core.rule import Rule
            from sortmeout.core.condition import Condition
            from sortmeout.core.action import Action
            from sortmeout.config.manager import ConfigManager

            parts = rule_spec.split("|")
            if len(parts) < 6:
                return (
                    f"❌ Invalid rule spec: need folder|attribute|operator|value|action|destination"
                )

            folder = os.path.expanduser(parts[0])
            attribute = parts[1]
            operator = parts[2]
            value = parts[3]
            action_type = parts[4]
            action_arg = os.path.expanduser(parts[5]) if parts[5] else ""

            # Build condition
            condition = Condition(attribute, operator, value)

            # Build action with proper params
            action_params = {}
            if action_type in ("move", "copy"):
                action_params["destination"] = action_arg
            elif action_type == "rename":
                action_params["new_name"] = action_arg
            elif action_type == "add_tags":
                action_params["tags"] = [action_arg]

            action = Action(action_type, **action_params)

            # Create the rule
            rule = Rule(
                name=rule_name,
                conditions=[condition],
                actions=[action],
                description=f"Created via AI chat on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            )

            # Save to config
            config_mgr = ConfigManager()
            config = config_mgr.load_config()

            # Ensure folder exists in config
            if "folders" not in config:
                config["folders"] = []

            # Find or create folder entry
            folder_entry = None
            for f in config["folders"]:
                if os.path.expanduser(f.get("path", "")) == folder or f.get("path", "") == parts[0]:
                    folder_entry = f
                    break

            if folder_entry is None:
                folder_entry = {"path": parts[0], "rules": []}
                config["folders"].append(folder_entry)

            if "rules" not in folder_entry:
                folder_entry["rules"] = []

            # Check for duplicate name
            for existing in folder_entry["rules"]:
                if existing.get("name") == rule_name:
                    return f'⚠️ A rule named "{rule_name}" already exists for {parts[0]}'

            folder_entry["rules"].append(rule.to_dict())
            config_mgr.save_config(config)

            return (
                f"✅ Rule created: **{rule_name}**\n"
                f"  📂 Folder: `{parts[0]}`\n"
                f'  🔍 When: {attribute} {operator} "{value}"\n'
                f"  ⚡ Then: {action_type}"
                + (f" → `{action_arg}`" if action_arg else "")
                + f"\n\n*Rule is saved and will activate when watching starts.*"
            )

        except Exception as e:
            return f"❌ Could not create rule: {str(e)}"

    # ── Shared integration command executor ──

    def _run_integration_command(self, action: str, arg1: str, arg2: str | None) -> str | None:
        """Execute an integration command and return result string, or None if not an integration command."""
        try:
            # ── Mail commands ──
            if action == "mail_unread":
                mail = _get_mail()
                count = mail.get_unread_count()
                return f"📧 You have **{count}** unread email(s)"

            elif action == "mail_recent":
                mail = _get_mail()
                count = int(arg1) if arg1 and arg1.isdigit() else 5
                emails = mail.get_recent_emails(count, unread_only=False)
                if emails:
                    lines = [f"📧 **{len(emails)} recent email(s):**"]
                    for e in emails:
                        flag = "🔵" if e.get("unread") else "  "
                        lines.append(
                            f"{flag} **{e.get('subject', '(no subject)')}** — {e.get('sender', '?')}"
                        )
                    return "\n".join(lines)
                return "📧 No recent emails found"

            elif action == "mail_read":
                mail = _get_mail()
                detail = mail.read_email(arg1)
                if "error" not in detail:
                    lines = [
                        f"📧 **{detail.get('subject', '(no subject)')}**",
                        f"From: {detail.get('sender', '?')}",
                        f"Date: {detail.get('date', '?')}",
                        f"",
                        detail.get("body", "(empty)")[:2000],
                    ]
                    return "\n".join(lines)
                return f"❌ {detail.get('error', 'Could not read email')}"

            elif action == "mail_search":
                mail = _get_mail()
                results = mail.search_emails(arg1)
                if results:
                    lines = [f'🔍 Found **{len(results)}** email(s) matching "{arg1}":']
                    for e in results[:10]:
                        lines.append(f"  - **{e.get('subject', '?')}** — {e.get('sender', '?')}")
                    return "\n".join(lines)
                return f'🔍 No emails found matching "{arg1}"'

            elif action == "mail_search_all":
                mail = _get_mail()
                results = mail.search_all_mailboxes(arg1)
                if results:
                    lines = [
                        f'🔍 Found **{len(results)}** email(s) matching "{arg1}" across all mailboxes:'
                    ]
                    for e in results[:10]:
                        mailbox = e.get("mailbox", "?")
                        lines.append(
                            f"  - [{mailbox}] **{e.get('subject', '?')}** — {e.get('sender', '?')}"
                        )
                    return "\n".join(lines)
                return f'🔍 No emails found matching "{arg1}" in any mailbox'

            elif action == "mail_compose":
                mail = _get_mail()
                # arg1 = "to" address, arg2 = "subject|body|attachment" (pipe separated)
                subject, body, attachment = "", "", None
                if arg2:
                    parts = arg2.split("|", 2)
                    subject = parts[0] if len(parts) >= 1 else ""
                    body = parts[1] if len(parts) >= 2 else ""
                    attachment = parts[2] if len(parts) >= 3 else None
                result = mail.compose_email(
                    to=arg1, subject=subject, body=body, attachment=attachment, send=False
                )
                if result.get("success"):
                    attach_str = f"\n  📎 Attachment: `{attachment}`" if attachment else ""
                    return f'📝 Draft created for **{arg1}** — subject: "{subject}"{attach_str}'
                return f"❌ Could not create draft: {result.get('error', '?')}"

            elif action == "mail_send":
                mail = _get_mail()
                subject, body, attachment = "", "", None
                if arg2:
                    parts = arg2.split("|", 2)
                    subject = parts[0] if len(parts) >= 1 else ""
                    body = parts[1] if len(parts) >= 2 else ""
                    attachment = parts[2] if len(parts) >= 3 else None
                result = mail.compose_email(
                    to=arg1, subject=subject, body=body, attachment=attachment, send=True
                )
                if result.get("success"):
                    attach_str = f" (📎 with attachment)" if attachment else ""
                    return f"📨 Email sent to **{arg1}**{attach_str}"
                return f"❌ Could not send email: {result.get('error', '?')}"

            elif action == "mail_reply":
                mail = _get_mail()
                result = mail.reply_to_email(arg1, arg2 or "", send=False)
                if result.get("success"):
                    return f"📝 Reply draft created"
                return f"❌ Could not create reply: {result.get('error', '?')}"

            elif action == "mail_reply_send":
                mail = _get_mail()
                result = mail.reply_to_email(arg1, arg2 or "", send=True)
                if result.get("success"):
                    return f"📨 Reply sent"
                return f"❌ Could not send reply: {result.get('error', '?')}"

            elif action == "mail_flag":
                mail = _get_mail()
                result = mail.mark_as_flagged(arg1)
                if result.get("success"):
                    return f"🚩 Email flagged"
                return f"❌ Could not flag email: {result.get('error', '?')}"

            elif action == "mail_markread":
                mail = _get_mail()
                result = mail.mark_as_read(arg1)
                if result.get("success"):
                    return f"✅ Email marked as read"
                return f"❌ Could not mark as read: {result.get('error', '?')}"

            # ── Calendar commands ──
            elif action == "cal_today":
                cal = _get_calendar()
                events = cal.get_events_today()
                if events:
                    lines = [f"📅 **{len(events)} event(s) today:**"]
                    for ev in events:
                        time_str = ev.get("start_time", "")
                        lines.append(f"  • {time_str} — **{ev.get('title', '?')}**")
                        if ev.get("location"):
                            lines.append(f"    📍 {ev['location']}")
                    return "\n".join(lines)
                return "📅 No events today — your day is clear!"

            elif action == "cal_tomorrow":
                cal = _get_calendar()
                events = cal.get_events_tomorrow()
                if events:
                    lines = [f"📅 **{len(events)} event(s) tomorrow:**"]
                    for ev in events:
                        lines.append(f"  • {ev.get('start_time', '')} — **{ev.get('title', '?')}**")
                    return "\n".join(lines)
                return "📅 No events tomorrow"

            elif action == "cal_week":
                cal = _get_calendar()
                events = cal.get_events_this_week()
                if events:
                    lines = [f"📅 **{len(events)} event(s) this week:**"]
                    for ev in events:
                        lines.append(
                            f"  • {ev.get('date', '')} {ev.get('start_time', '')} — **{ev.get('title', '?')}**"
                        )
                    return "\n".join(lines)
                return "📅 No events this week"

            elif action == "cal_upcoming":
                cal = _get_calendar()
                days = int(arg1) if arg1 and arg1.isdigit() else 7
                events = cal.get_upcoming_events(days)
                if events:
                    lines = [f"📅 **{len(events)} upcoming event(s) ({days} days):**"]
                    for ev in events:
                        lines.append(
                            f"  • {ev.get('date', '')} {ev.get('start_time', '')} — **{ev.get('title', '?')}**"
                        )
                    return "\n".join(lines)
                return f"📅 No upcoming events in the next {days} days"

            elif action == "cal_search":
                cal = _get_calendar()
                events = cal.search_events(arg1)
                if events:
                    lines = [f'🔍 Found **{len(events)}** event(s) matching "{arg1}":']
                    for ev in events:
                        lines.append(f"  • {ev.get('date', '')} — **{ev.get('title', '?')}**")
                    return "\n".join(lines)
                return f'🔍 No events found matching "{arg1}"'

            elif action == "cal_deadlines":
                cal = _get_calendar()
                days = int(arg1) if arg1 and arg1.isdigit() else 7
                deadlines = cal.get_deadlines(days)
                if deadlines:
                    lines = [f"⏰ **{len(deadlines)} deadline(s) in {days} days:**"]
                    for d in deadlines:
                        lines.append(f"  • {d.get('date', '')} — **{d.get('title', '?')}**")
                    return "\n".join(lines)
                return f"⏰ No deadlines in the next {days} days"

            elif action == "cal_create":
                cal = _get_calendar()
                # arg1 = title, arg2 = start datetime string
                result = cal.create_event(title=arg1, start=arg2 or "")
                if result.get("success"):
                    return f"📅 Event created: **{arg1}**"
                return f"❌ Could not create event: {result.get('error', '?')}"

            elif action == "cal_briefing":
                cal = _get_calendar()
                briefing = cal.get_daily_briefing()
                return f"📅 **Daily Briefing:**\n{briefing}"

            elif action == "cal_edit":
                cal = _get_calendar()
                # arg1 = event title, arg2 = "new_title|new_start|new_end|new_location|new_notes"
                new_title, new_start, new_end, new_location, new_notes = (
                    None,
                    None,
                    None,
                    None,
                    None,
                )
                if arg2:
                    parts = arg2.split("|")
                    if len(parts) >= 1 and parts[0].strip():
                        new_title = parts[0].strip()
                    if len(parts) >= 2 and parts[1].strip():
                        new_start = parts[1].strip()
                    if len(parts) >= 3 and parts[2].strip():
                        new_end = parts[2].strip()
                    if len(parts) >= 4 and parts[3].strip():
                        new_location = parts[3].strip()
                    if len(parts) >= 5 and parts[4].strip():
                        new_notes = parts[4].strip()
                result = cal.edit_event(
                    arg1,
                    new_title=new_title,
                    new_start=new_start,
                    new_end=new_end,
                    new_location=new_location,
                    new_notes=new_notes,
                )
                if result.get("success"):
                    return f"✏️ Event edited: **{arg1}**"
                return f"❌ {result.get('error', 'Could not edit event')}"

            elif action == "cal_delete":
                cal = _get_calendar()
                result = cal.delete_event(arg1)
                if result.get("success"):
                    return f"🗑️ Event deleted: **{arg1}**"
                return f"❌ {result.get('error', 'Could not delete event')}"

            # ── Messages commands ──
            elif action == "msg_chats":
                msgs = _get_messages()
                count = int(arg1) if arg1 and arg1.isdigit() else 5
                chats = msgs.get_recent_chats(count)
                if chats:
                    lines = [f"💬 **{len(chats)} recent chat(s):**"]
                    for c in chats:
                        preview = c.get("last_message", "")[:60]
                        lines.append(f"  • **{c.get('name', '?')}**: {preview}")
                    return "\n".join(lines)
                return "💬 No recent chats"

            elif action == "msg_send":
                msgs = _get_messages()
                result = msgs.send_message(arg1, arg2 or "")
                if result.get("success"):
                    return f"💬 Message sent to **{arg1}**"
                return f"❌ Could not send message: {result.get('error', '?')}"

            elif action == "msg_read":
                msgs = _get_messages()
                count = 10
                if arg2 and arg2.isdigit():
                    count = int(arg2)
                messages = msgs.read_messages(contact=arg1, count=count)
                if messages:
                    lines = [f"💬 **Last {len(messages)} message(s) with {arg1}:**"]
                    for m in messages:
                        who = "🟢 Me" if m.get("is_from_me") else f"🔵 {m.get('sender', '?')}"
                        lines.append(f"  {m.get('date', '')} | {who}: {m.get('text', '')[:200]}")
                    return "\n".join(lines)
                return f"💬 No messages found with {arg1}"

            # ── Contacts commands ──
            elif action == "contact_search":
                contacts = _get_contacts()
                results = contacts.search(arg1)
                if results:
                    lines = [f'👤 Found **{len(results)}** contact(s) matching "{arg1}":']
                    for c in results[:10]:
                        info_parts = [c.get("name", "?")]
                        if c.get("phone"):
                            info_parts.append(f"📱 {c['phone']}")
                        if c.get("email"):
                            info_parts.append(f"✉️ {c['email']}")
                        lines.append(f"  • {' | '.join(info_parts)}")
                    return "\n".join(lines)
                return f'👤 No contacts found matching "{arg1}"'

            elif action == "contact_groups":
                contacts = _get_contacts()
                groups = contacts.get_groups()
                if groups:
                    lines = [f"👥 **Contact groups ({len(groups)}):**"]
                    for g in groups:
                        lines.append(f"  • {g}")
                    return "\n".join(lines)
                return "👥 No contact groups found"

            elif action == "contact_create":
                contacts = _get_contacts()
                # arg1 = "first|last|phone|email|org|note" (pipe separated)
                first, last, phone, email, org, note = "", "", "", "", "", ""
                if arg1:
                    parts = arg1.split("|")
                    if len(parts) >= 1:
                        first = parts[0].strip()
                    if len(parts) >= 2:
                        last = parts[1].strip()
                    if len(parts) >= 3:
                        phone = parts[2].strip()
                    if len(parts) >= 4:
                        email = parts[3].strip()
                    if len(parts) >= 5:
                        org = parts[4].strip()
                    if len(parts) >= 6:
                        note = parts[5].strip()
                if not first:
                    return "❌ First name is required to create a contact"
                result = contacts.create_contact(
                    first_name=first,
                    last_name=last,
                    phone=phone,
                    email=email,
                    organization=org,
                    note=note,
                )
                if result.get("success"):
                    return f"👤 Contact created: **{result.get('name', first)}**"
                return f"❌ Could not create contact: {result.get('error', '?')}"

            elif action == "contact_edit":
                contacts = _get_contacts()
                # arg1 = name to search, arg2 = "new_phone|new_email|new_org|new_note"
                new_phone, new_email, new_org, new_note = "", "", "", ""
                if arg2:
                    parts = arg2.split("|")
                    if len(parts) >= 1:
                        new_phone = parts[0].strip()
                    if len(parts) >= 2:
                        new_email = parts[1].strip()
                    if len(parts) >= 3:
                        new_org = parts[2].strip()
                    if len(parts) >= 4:
                        new_note = parts[3].strip()
                result = contacts.edit_contact(
                    search_name=arg1,
                    new_phone=new_phone,
                    new_email=new_email,
                    new_organization=new_org,
                    new_note=new_note,
                )
                if result.get("success"):
                    return f"✏️ Contact edited: **{arg1}**"
                return f"❌ {result.get('error', 'Could not edit contact')}"

            elif action == "contact_delete":
                contacts = _get_contacts()
                result = contacts.delete_contact(arg1)
                if result.get("success"):
                    return f"🗑️ Contact deleted: **{arg1}**"
                return f"❌ {result.get('error', 'Could not delete contact')}"

            # ── Presentations commands ──
            elif action == "pres_create":
                pres = _get_presentations()
                # arg1 = title, arg2 = outline (markdown-style, newlines as \n)
                if arg2:
                    result = pres.create_from_outline(arg2)
                else:
                    result = pres.create_presentation(title=arg1, slides=[])
                if result.get("success"):
                    path = result.get("path", "")
                    return f"📊 Presentation created: **{arg1}**\n  → `{path}`"
                return f"❌ Could not create presentation: {result.get('error', '?')}"

            # ── Notes commands ──
            elif action == "notes_recent":
                notes = _get_notes()
                count = int(arg1) if arg1 and arg1.isdigit() else 5
                recent = notes.get_recent_notes(count)
                if recent:
                    lines = [f"📝 **{len(recent)} recent note(s):**"]
                    for n in recent:
                        lines.append(f"  • **{n.get('name', '?')}** — {n.get('snippet', '')[:60]}")
                    return "\n".join(lines)
                return "📝 No recent notes"

            elif action == "notes_read":
                notes = _get_notes()
                content = notes.read_note(arg1)
                if content and "error" not in content:
                    body = content.get("body", "(empty)")[:3000]
                    return f"📝 **{arg1}**\n\n{body}"
                return f"❌ Could not read note: {content.get('error', '?') if content else 'not found'}"

            elif action == "notes_create":
                notes = _get_notes()
                result = notes.create_note(title=arg1, body=arg2 or "")
                if result.get("success"):
                    return f"📝 Note created: **{arg1}**"
                return f"❌ Could not create note: {result.get('error', '?')}"

            elif action == "notes_search":
                notes = _get_notes()
                results = notes.search_notes(arg1)
                if results:
                    lines = [f'🔍 Found **{len(results)}** note(s) matching "{arg1}":']
                    for n in results[:10]:
                        lines.append(f"  • **{n.get('name', '?')}**")
                    return "\n".join(lines)
                return f'🔍 No notes found matching "{arg1}"'

            elif action == "notes_append":
                notes = _get_notes()
                result = notes.append_to_note(arg1, arg2 or "")
                if result.get("success"):
                    return f"📝 Appended to note: **{arg1}**"
                return f"❌ Could not append to note: {result.get('error', '?')}"

            elif action == "notes_edit":
                notes = _get_notes()
                result = notes.edit_note(arg1, arg2 or "")
                if result.get("success"):
                    return f"📝 Note edited: **{arg1}**"
                return f"❌ Could not edit note: {result.get('error', '?')}"

            elif action == "notes_delete":
                notes = _get_notes()
                result = notes.delete_note(arg1)
                if result.get("success"):
                    return f"🗑️ Note deleted: **{arg1}**"
                return f"❌ {result.get('error', 'Could not delete note')}"

            # ── Image commands ──
            elif action == "img_generate":
                gen = _get_image_generator()
                if not gen.is_available:
                    return "❌ AI image generation unavailable — set OPENAI_API_KEY environment variable"
                # arg1 = prompt, arg2 = "size|quality|style" (optional)
                size, quality, style = "1024x1024", "hd", "vivid"
                if arg2:
                    parts = arg2.split("|")
                    if len(parts) >= 1 and parts[0]:
                        size = parts[0]
                    if len(parts) >= 2 and parts[1]:
                        quality = parts[1]
                    if len(parts) >= 3 and parts[2]:
                        style = parts[2]
                result = gen.generate(prompt=arg1, size=size, quality=quality, style=style)
                if result.get("success"):
                    return (
                        f"🎨 **Image generated!**\n"
                        f"  → `{result['path']}`\n"
                        f"  Size: {result.get('size', '?')} | Quality: {result.get('quality', '?')}\n"
                        f"  File: {result.get('file_size', '?')}\n"
                        f"  Revised prompt: _{result.get('revised_prompt', '')[:150]}_"
                    )
                return f"❌ Image generation failed: {result.get('error', '?')}"

            elif action == "img_edit_ai":
                gen = _get_image_generator()
                if not gen.is_available:
                    return (
                        "❌ AI image editing unavailable — set OPENAI_API_KEY environment variable"
                    )
                result = gen.edit_with_ai(path=arg1, prompt=arg2 or "")
                if result.get("success"):
                    return f"🎨 **Image edited with AI!**\n  → `{result['path']}`"
                return f"❌ AI image edit failed: {result.get('error', '?')}"

            elif action == "img_resize":
                editor = _get_image_editor()
                # arg1 = path, arg2 = "width|height"
                w, h = 0, 0
                if arg2:
                    parts = arg2.split("|")
                    w = int(parts[0]) if len(parts) >= 1 and parts[0].isdigit() else 0
                    h = int(parts[1]) if len(parts) >= 2 and parts[1].isdigit() else 0
                result = editor.resize(arg1, width=w, height=h)
                if result.get("success"):
                    return f"📐 Resized: {result['original_size']} → {result['new_size']}\n  → `{result['path']}`"
                return f"❌ Resize failed: {result.get('error', '?')}"

            elif action == "img_crop":
                editor = _get_image_editor()
                # arg2 = "left|top|right|bottom"
                if not arg2:
                    return "❌ Crop requires coordinates: left|top|right|bottom"
                parts = arg2.split("|")
                if len(parts) < 4:
                    return "❌ Crop requires 4 values: left|top|right|bottom"
                left, top, right, bottom = (
                    int(parts[0]),
                    int(parts[1]),
                    int(parts[2]),
                    int(parts[3]),
                )
                result = editor.crop(arg1, left, top, right, bottom)
                if result.get("success"):
                    return f"✂️ Cropped to {result['new_size']}\n  → `{result['path']}`"
                return f"❌ Crop failed: {result.get('error', '?')}"

            elif action == "img_rotate":
                editor = _get_image_editor()
                degrees = float(arg2) if arg2 else 90.0
                result = editor.rotate(arg1, degrees)
                if result.get("success"):
                    return f"🔄 Rotated {result['degrees']}° → {result['new_size']}\n  → `{result['path']}`"
                return f"❌ Rotate failed: {result.get('error', '?')}"

            elif action == "img_flip":
                editor = _get_image_editor()
                direction = arg2 or "horizontal"
                result = editor.flip(arg1, direction)
                if result.get("success"):
                    return f"🔃 Flipped {result['direction']}\n  → `{result['path']}`"
                return f"❌ Flip failed: {result.get('error', '?')}"

            elif action == "img_filter":
                editor = _get_image_editor()
                # arg2 = "filter_name|intensity"
                filter_name = "grayscale"
                intensity = 1.0
                if arg2:
                    parts = arg2.split("|")
                    filter_name = parts[0].strip()
                    if len(parts) >= 2:
                        try:
                            intensity = float(parts[1])
                        except ValueError:
                            pass
                result = editor.apply_filter(arg1, filter_name, intensity)
                if result.get("success"):
                    return f"🎨 Filter **{result['filter']}** applied (intensity: {result['intensity']})\n  → `{result['path']}`"
                return f"❌ Filter failed: {result.get('error', '?')}"

            elif action == "img_text":
                editor = _get_image_editor()
                # arg2 = "text|position|font_size|color"
                text, position, font_size, color = "SortMeOut", "bottom-right", 40, "white"
                if arg2:
                    parts = arg2.split("|")
                    if len(parts) >= 1:
                        text = parts[0]
                    if len(parts) >= 2:
                        position = parts[1].strip()
                    if len(parts) >= 3 and parts[2].strip().isdigit():
                        font_size = int(parts[2])
                    if len(parts) >= 4:
                        color = parts[3].strip()
                result = editor.add_text(
                    arg1, text, position=position, font_size=font_size, color=color
                )
                if result.get("success"):
                    return f"✏️ Text overlay added: \"{text}\"\n  → `{result['path']}`"
                return f"❌ Text overlay failed: {result.get('error', '?')}"

            elif action == "img_convert":
                editor = _get_image_editor()
                # arg2 = "format|quality"
                fmt = "png"
                quality = 95
                if arg2:
                    parts = arg2.split("|")
                    fmt = parts[0].strip()
                    if len(parts) >= 2 and parts[1].strip().isdigit():
                        quality = int(parts[1])
                result = editor.convert(arg1, fmt, quality=quality)
                if result.get("success"):
                    return f"🔄 Converted to **{result['format']}** ({result['size']})\n  → `{result['path']}`"
                return f"❌ Convert failed: {result.get('error', '?')}"

            elif action == "img_compress":
                editor = _get_image_editor()
                # arg2 = "quality|max_width"
                quality = 70
                max_width = 0
                if arg2:
                    parts = arg2.split("|")
                    if len(parts) >= 1 and parts[0].strip().isdigit():
                        quality = int(parts[0])
                    if len(parts) >= 2 and parts[1].strip().isdigit():
                        max_width = int(parts[1])
                result = editor.compress(arg1, quality=quality, max_width=max_width)
                if result.get("success"):
                    return (
                        f"📦 Compressed: {result['original_size']} → {result['new_size']} "
                        f"(−{result['reduction']})\n  → `{result['path']}`"
                    )
                return f"❌ Compress failed: {result.get('error', '?')}"

            elif action == "img_info":
                editor = _get_image_editor()
                info = editor.get_info(arg1)
                if "error" not in info:
                    return (
                        f"🖼️ **Image Info:**\n"
                        f"  Format: {info['format']} | Mode: {info['mode']}\n"
                        f"  Dimensions: {info['width']}×{info['height']}\n"
                        f"  Size: {info['size_human']}\n"
                        f"  Alpha: {'Yes' if info.get('has_alpha') else 'No'}"
                    )
                return f"❌ Could not read image: {info.get('error', '?')}"

        except Exception as e:
            return f"❌ {action} failed: {str(e)[:100]}"

        return None  # Not an integration command

    def _execute_pending_commands(self) -> str:
        """Execute all pending commands."""
        import shutil
        import os
        from pathlib import Path
        from sortmeout.macos import system as macos_sys

        if not hasattr(self, "pending_commands") or not self.pending_commands:
            return "\n\n*No pending commands to execute.*"

        successful = []
        failed = []

        # Track moves by destination for grouped reporting
        moves_by_dest = {}  # dest_folder -> [(src_name, full_dest_path), ...]

        for match in self.pending_commands:
            action = match[0]
            path1 = os.path.expanduser(match[1]) if match[1] else ""
            path2 = os.path.expanduser(match[2]) if match[2] else None

            try:
                if action == "mkdir":
                    os.makedirs(path1, exist_ok=True)
                    successful.append(f"📁 Created: `{path1}`")
                elif action == "move" and path2:
                    src = Path(path1)
                    if src.exists():
                        os.makedirs(path2, exist_ok=True)
                        dest = Path(path2) / src.name
                        shutil.move(str(src), str(dest))
                        moves_by_dest.setdefault(path2, []).append((src.name, str(dest)))
                        successful.append(f"📦 {src.name} → `{dest}`")
                        get_history().record(
                            action_type="move",
                            source_path=str(src),
                            destination_path=str(dest),
                            rule_name="AI Assistant",
                            metadata={"via": "ai_pending_cmd"},
                        )
                    else:
                        failed.append(f"❌ {Path(path1).name} (not found)")
                elif action == "trash":
                    import subprocess

                    if os.path.exists(path1):
                        subprocess.run(
                            [
                                "osascript",
                                "-e",
                                f'tell application "Finder" to delete POSIX file "{path1}"',
                            ],
                            check=True,
                            capture_output=True,
                        )
                        successful.append(f"🗑️ {Path(path1).name}")
                        get_history().record(
                            action_type="trash",
                            source_path=path1,
                            rule_name="AI Assistant",
                            metadata={"via": "ai_pending_cmd"},
                        )
                    else:
                        failed.append(f"❌ {Path(path1).name} (not found)")
                elif action == "copy" and path2:
                    src = Path(path1)
                    if src.exists():
                        os.makedirs(path2, exist_ok=True)
                        dest = Path(path2) / src.name
                        shutil.copy2(str(src), str(dest))
                        moves_by_dest.setdefault(path2, []).append((src.name, str(dest)))
                        successful.append(f"📋 {src.name} → `{dest}`")
                        get_history().record(
                            action_type="copy",
                            source_path=str(src),
                            destination_path=str(dest),
                            rule_name="AI Assistant",
                            metadata={"via": "ai_pending_cmd"},
                        )
                elif action == "rename" and path2:
                    src = Path(path1)
                    if src.exists():
                        new_path = src.parent / path2
                        src.rename(new_path)
                        successful.append(f"✏️ {src.name} → `{new_path}`")
                        get_history().record(
                            action_type="rename",
                            source_path=str(src),
                            destination_path=str(new_path),
                            rule_name="AI Assistant",
                            metadata={"via": "ai_pending_cmd"},
                        )
                elif action == "open":
                    import subprocess

                    if os.path.exists(path1):
                        subprocess.Popen(["open", path1])
                        successful.append(f"📂 Opened: `{path1}`")
                    else:
                        failed.append(f"❌ {Path(path1).name} (not found)")
                elif action == "openapp":
                    import subprocess

                    subprocess.Popen(["open", "-a", path1])
                    successful.append(f"🚀 Launched: {path1}")

                # ── New system commands ──
                elif action == "search":
                    results = macos_sys.search_files(path1)
                    if results:
                        lines = [f'🔍 Found {len(results)} result(s) for "{path1}":']
                        for r in results[:15]:
                            icon = "📁" if r.get("is_dir") else "📄"
                            lines.append(f"  {icon} `{r['path']}`")
                        if len(results) > 15:
                            lines.append(f"  ... and {len(results) - 15} more")
                        successful.append("\n".join(lines))
                    else:
                        successful.append(f'🔍 No results for "{path1}"')

                elif action == "tag" and path2:
                    from sortmeout.macos.tags import add_tags

                    if os.path.exists(path1):
                        add_tags(path1, [path2])
                        successful.append(f'🏷️ Tagged `{Path(path1).name}` with "{path2}"')
                    else:
                        failed.append(f"❌ {Path(path1).name} (not found)")

                elif action == "untag" and path2:
                    from sortmeout.macos.tags import remove_tags

                    if os.path.exists(path1):
                        remove_tags(path1, [path2])
                        successful.append(f'🏷️ Removed tag "{path2}" from `{Path(path1).name}`')
                    else:
                        failed.append(f"❌ {Path(path1).name} (not found)")

                elif action == "reveal":
                    if macos_sys.reveal_in_finder(path1):
                        successful.append(f"📂 Revealed in Finder: `{path1}`")
                    else:
                        failed.append(f"❌ Could not reveal: `{path1}`")

                elif action == "compress":
                    archive = macos_sys.compress(path1)
                    if archive:
                        successful.append(f"🗜️ Compressed → `{archive}`")
                    else:
                        failed.append(f"❌ Could not compress: `{path1}`")

                elif action == "decompress":
                    dest = macos_sys.decompress(path1, path2)
                    if dest:
                        successful.append(f"📦 Extracted → `{dest}`")
                    else:
                        failed.append(f"❌ Could not decompress: `{path1}`")

                elif action == "getinfo":
                    info = macos_sys.get_file_info_detailed(path1)
                    if "error" not in info:
                        lines = [f"ℹ️ **{info.get('name', path1)}**"]
                        for k, v in info.items():
                            if k not in ("name", "path") and v is not None:
                                lines.append(f"  {k}: {v}")
                        successful.append("\n".join(lines))
                    else:
                        failed.append(f"❌ {info['error']}")

                elif action == "emptytrash":
                    if macos_sys.empty_trash_system():
                        successful.append("🗑️ Trash emptied!")
                    else:
                        failed.append("❌ Could not empty trash")

                elif action == "notify":
                    title = path1 or "SortMeOut"
                    msg = path2 or ""
                    macos_sys.send_notification(title, msg)
                    successful.append(f'🔔 Notification sent: "{title}"')

                elif action == "clipboard":
                    if macos_sys.clipboard_copy(path1):
                        preview = path1[:50] + "..." if len(path1) > 50 else path1
                        successful.append(f'📋 Copied to clipboard: "{preview}"')
                    else:
                        failed.append("❌ Could not copy to clipboard")

                elif action == "screenshot":
                    shot = macos_sys.take_screenshot()
                    if shot:
                        successful.append(f"📸 Screenshot saved: `{shot}`")
                    else:
                        failed.append("❌ Screenshot failed")

                elif action == "darkmode":
                    new_mode = macos_sys.toggle_dark_mode()
                    successful.append(f"🌓 Switched to **{new_mode} mode**")

                elif action == "volume":
                    try:
                        level = int(path1)
                        macos_sys.set_volume(level)
                        successful.append(f"🔊 Volume set to {level}%")
                    except ValueError:
                        failed.append(f"❌ Invalid volume level: {path1}")

                elif action == "mute":
                    if macos_sys.toggle_mute():
                        successful.append("🔇 Mute toggled")
                    else:
                        failed.append("❌ Could not toggle mute")

                elif action == "preview":
                    if macos_sys.quick_look(path1):
                        successful.append(f"👁️ Quick Look: `{Path(path1).name}`")
                    else:
                        failed.append(f"❌ Could not preview: `{path1}`")

                elif action == "killprocess":
                    macos_sys.kill_process(path1)
                    successful.append(f"💀 Killed process: {path1}")

                elif action == "diskspace":
                    info = macos_sys.get_disk_space()
                    if info:
                        successful.append(
                            f"💾 Disk: {info.get('used', '?')} used / "
                            f"{info.get('available', '?')} free "
                            f"({info.get('percent_used', '?')})"
                        )
                    else:
                        failed.append("❌ Could not get disk info")

                elif action == "battery":
                    info = macos_sys.get_battery_info()
                    if info:
                        pct = info.get("percentage", "?")
                        src = info.get("power_source", "?")
                        remaining = info.get("time_remaining", "")
                        icon = "🔌" if src == "AC Power" else "🔋"
                        msg = f"{icon} Battery: {pct}% ({src})"
                        if remaining:
                            msg += f" — {remaining} remaining"
                        successful.append(msg)
                    else:
                        failed.append("❌ Could not get battery info")

                elif action == "wifi":
                    info = macos_sys.get_wifi_info()
                    if info.get("connected"):
                        successful.append(f"📶 WiFi: Connected to **{info['network']}**")
                    else:
                        successful.append("📶 WiFi: Not connected")

                elif action == "lockscreen":
                    macos_sys.lock_screen()
                    successful.append("🔒 Screen locked")

                elif action == "say":
                    macos_sys.text_to_speech(path1)
                    successful.append(f'🗣️ Speaking: "{path1[:50]}"')

                elif action == "eject":
                    if macos_sys.eject_volume(path1):
                        successful.append(f"⏏️ Ejected: {path1}")
                    else:
                        failed.append(f"❌ Could not eject: {path1}")

                elif action == "symlink" and path2:
                    if macos_sys.create_symlink(path1, path2):
                        successful.append(f"🔗 Symlink: `{path2}` → `{path1}`")
                    else:
                        failed.append(f"❌ Could not create symlink")

                elif action == "wallpaper":
                    if macos_sys.set_wallpaper(path1):
                        successful.append(f"🖼️ Wallpaper set: `{path1}`")
                    else:
                        failed.append(f"❌ Could not set wallpaper: `{path1}`")

                elif action == "hiddenfiles":
                    state = macos_sys.toggle_hidden_files()
                    successful.append(f"👻 Hidden files are now **{state}**")

                elif action == "runningapps":
                    apps = macos_sys.get_running_apps()
                    if apps:
                        lines = [f"📱 Running apps ({len(apps)}):"]
                        for a in apps:
                            lines.append(f"  • {a}")
                        successful.append("\n".join(lines))
                    else:
                        successful.append("📱 No running apps found")

                elif action == "foldersize":
                    size = macos_sys.get_folder_size(path1)
                    if size:
                        successful.append(f"📊 `{path1}`: {size}")
                    else:
                        failed.append(f"❌ Could not get size for: `{path1}`")

                elif action == "createrule" and path2:
                    result_msg = self._create_rule_from_chat(path1, path2)
                    if result_msg.startswith("✅"):
                        successful.append(result_msg)
                    else:
                        failed.append(result_msg)

                elif action == "renameai" and path1:
                    from sortmeout.gui.chat_window import _save_ai_name

                    if _save_ai_name(path1):
                        successful.append(
                            f"✅ Assistant renamed to **{path1}** — restart chat to see the change"
                        )
                    else:
                        failed.append(f"❌ Could not save assistant name")

                else:
                    # ── Integration commands (mail, calendar, messages, etc.) ──
                    integration_result = self._run_integration_command(action, path1, path2)
                    if integration_result is not None:
                        if integration_result.startswith("❌"):
                            failed.append(integration_result)
                        else:
                            successful.append(integration_result)

            except Exception as e:
                failed.append(f"❌ {action} {Path(path1).name if path1 else ''}: {str(e)[:50]}")

        # Build result report with full paths
        result = "\n\n---\n"
        if successful:
            result += f"\n✅ **{len(successful)} action(s) completed**\n\n"

        # Grouped path summary for moves/copies
        if moves_by_dest:
            for dest_folder, files in moves_by_dest.items():
                if len(files) == 1:
                    name, full_path = files[0]
                    result += f"- **{name}** → `{full_path}`\n"
                else:
                    result += f"\n**→ `{dest_folder}`** ({len(files)} files)\n"
                    for name, full_path in files:
                        result += f"  - {name}\n"

        # Non-move results (system commands, etc.)
        non_move = [s for s in successful if not s.startswith("📦 ") and not s.startswith("📋 ")]
        for item in non_move:
            result += f"\n{item}\n"

        if failed:
            result += f"\n⚠️ **{len(failed)} failed**\n"
            for f in failed[:5]:
                result += f"  {f}\n"

        # Refresh folder structure
        if successful:
            self._load_folder_structure()

        return result

    def _execute_commands_in_response(self, response: str) -> str:
        """Parse and execute [EXECUTE: ...] commands in the response."""
        import re
        import shutil
        from sortmeout.macos import system as macos_sys

        # Find all EXECUTE commands
        matches = re.findall(self._command_pattern, response)

        if not matches:
            return response  # No commands to run

        successful = []
        failed = []
        moves_by_dest = {}  # dest_folder -> [(src_name, full_dest_path), ...]

        for match in matches:
            action = match[0]
            path1 = os.path.expanduser(match[1]) if match[1] else ""
            path2 = os.path.expanduser(match[2]) if match[2] else None

            try:
                if action == "mkdir":
                    os.makedirs(path1, exist_ok=True)
                    successful.append(f"📁 Created: `{path1}`")

                elif action == "move":
                    if path2:
                        src = Path(path1)
                        if src.exists():
                            os.makedirs(path2, exist_ok=True)
                            dest = Path(path2) / src.name
                            shutil.move(str(src), str(dest))
                            moves_by_dest.setdefault(path2, []).append((src.name, str(dest)))
                            successful.append(f"✅ {src.name} → `{dest}`")
                            get_history().record(
                                action_type="move",
                                source_path=str(src),
                                destination_path=str(dest),
                                rule_name="AI Assistant",
                                metadata={"via": "ai_chat_cmd"},
                            )
                        else:
                            failed.append(f"❌ Not found: `{path1}`")
                    else:
                        failed.append(f"❌ No destination for: {Path(path1).name}")

                elif action == "copy":
                    if path2:
                        src = Path(path1)
                        if src.exists():
                            os.makedirs(path2, exist_ok=True)
                            dest = Path(path2) / src.name
                            if src.is_dir():
                                shutil.copytree(str(src), str(dest))
                            else:
                                shutil.copy2(str(src), str(dest))
                            moves_by_dest.setdefault(path2, []).append((src.name, str(dest)))
                            successful.append(f"📋 {src.name} → `{dest}`")
                            get_history().record(
                                action_type="copy",
                                source_path=str(src),
                                destination_path=str(dest),
                                rule_name="AI Assistant",
                                metadata={"via": "ai_chat_cmd"},
                            )
                        else:
                            failed.append(f"❌ Not found: `{path1}`")

                elif action == "rename":
                    if path2:
                        src = Path(path1)
                        if src.exists():
                            new_path = src.parent / path2
                            src.rename(new_path)
                            successful.append(f"✏️ {src.name} → `{new_path}`")
                            get_history().record(
                                action_type="rename",
                                source_path=str(src),
                                destination_path=str(new_path),
                                rule_name="AI Assistant",
                                metadata={"via": "ai_chat_cmd"},
                            )
                        else:
                            failed.append(f"❌ Not found: `{path1}`")

                elif action == "trash":
                    import subprocess

                    if os.path.exists(path1):
                        subprocess.run(
                            [
                                "osascript",
                                "-e",
                                f'tell application "Finder" to delete POSIX file "{path1}"',
                            ],
                            check=True,
                            capture_output=True,
                        )
                        successful.append(f"🗑️ Trashed: `{path1}`")
                        get_history().record(
                            action_type="trash",
                            source_path=path1,
                            rule_name="AI Assistant",
                            metadata={"via": "ai_chat_cmd"},
                        )
                    else:
                        failed.append(f"❌ Not found: `{path1}`")

                elif action == "open":
                    import subprocess

                    if os.path.exists(path1):
                        subprocess.Popen(["open", path1])
                        successful.append(f"📂 Opened: `{path1}`")
                    else:
                        failed.append(f"❌ Not found: `{path1}`")

                elif action == "openapp":
                    import subprocess

                    subprocess.Popen(["open", "-a", path1])
                    successful.append(f"🚀 Launched: {path1}")

                # ── New system commands ──
                elif action == "search":
                    results = macos_sys.search_files(path1)
                    if results:
                        lines = [f'🔍 Found {len(results)} result(s) for "{path1}":']
                        for r in results[:15]:
                            icon = "📁" if r.get("is_dir") else "📄"
                            lines.append(f"  {icon} `{r['path']}`")
                        if len(results) > 15:
                            lines.append(f"  ... and {len(results) - 15} more")
                        successful.append("\n".join(lines))
                    else:
                        successful.append(f'🔍 No results for "{path1}"')

                elif action == "tag" and path2:
                    from sortmeout.macos.tags import add_tags

                    if os.path.exists(path1):
                        add_tags(path1, [path2])
                        successful.append(f'🏷️ Tagged `{Path(path1).name}` with "{path2}"')
                    else:
                        failed.append(f"❌ {Path(path1).name} (not found)")

                elif action == "untag" and path2:
                    from sortmeout.macos.tags import remove_tags

                    if os.path.exists(path1):
                        remove_tags(path1, [path2])
                        successful.append(f'🏷️ Removed tag "{path2}" from `{Path(path1).name}`')
                    else:
                        failed.append(f"❌ {Path(path1).name} (not found)")

                elif action == "reveal":
                    if macos_sys.reveal_in_finder(path1):
                        successful.append(f"📂 Revealed in Finder: `{path1}`")
                    else:
                        failed.append(f"❌ Could not reveal: `{path1}`")

                elif action == "compress":
                    archive = macos_sys.compress(path1)
                    if archive:
                        successful.append(f"🗜️ Compressed → `{archive}`")
                    else:
                        failed.append(f"❌ Could not compress: `{path1}`")

                elif action == "decompress":
                    dest = macos_sys.decompress(path1, path2)
                    if dest:
                        successful.append(f"📦 Extracted → `{dest}`")
                    else:
                        failed.append(f"❌ Could not decompress: `{path1}`")

                elif action == "getinfo":
                    info = macos_sys.get_file_info_detailed(path1)
                    if "error" not in info:
                        lines = [f"ℹ️ **{info.get('name', path1)}**"]
                        for k, v in info.items():
                            if k not in ("name", "path") and v is not None:
                                lines.append(f"  {k}: {v}")
                        successful.append("\n".join(lines))
                    else:
                        failed.append(f"❌ {info['error']}")

                elif action == "emptytrash":
                    if macos_sys.empty_trash_system():
                        successful.append("🗑️ Trash emptied!")
                    else:
                        failed.append("❌ Could not empty trash")

                elif action == "notify":
                    title = path1 or "SortMeOut"
                    msg = path2 or ""
                    macos_sys.send_notification(title, msg)
                    successful.append(f'🔔 Notification sent: "{title}"')

                elif action == "clipboard":
                    if macos_sys.clipboard_copy(path1):
                        preview = path1[:50] + "..." if len(path1) > 50 else path1
                        successful.append(f'📋 Copied to clipboard: "{preview}"')
                    else:
                        failed.append("❌ Could not copy to clipboard")

                elif action == "screenshot":
                    shot = macos_sys.take_screenshot()
                    if shot:
                        successful.append(f"📸 Screenshot saved: `{shot}`")
                    else:
                        failed.append("❌ Screenshot failed")

                elif action == "darkmode":
                    new_mode = macos_sys.toggle_dark_mode()
                    successful.append(f"🌓 Switched to **{new_mode} mode**")

                elif action == "volume":
                    try:
                        level = int(path1)
                        macos_sys.set_volume(level)
                        successful.append(f"🔊 Volume set to {level}%")
                    except ValueError:
                        failed.append(f"❌ Invalid volume level: {path1}")

                elif action == "mute":
                    if macos_sys.toggle_mute():
                        successful.append("🔇 Mute toggled")
                    else:
                        failed.append("❌ Could not toggle mute")

                elif action == "preview":
                    if macos_sys.quick_look(path1):
                        successful.append(f"👁️ Quick Look: `{Path(path1).name}`")
                    else:
                        failed.append(f"❌ Could not preview: `{path1}`")

                elif action == "killprocess":
                    macos_sys.kill_process(path1)
                    successful.append(f"💀 Killed process: {path1}")

                elif action == "diskspace":
                    info = macos_sys.get_disk_space()
                    if info:
                        successful.append(
                            f"💾 Disk: {info.get('used', '?')} used / "
                            f"{info.get('available', '?')} free "
                            f"({info.get('percent_used', '?')})"
                        )
                    else:
                        failed.append("❌ Could not get disk info")

                elif action == "battery":
                    info = macos_sys.get_battery_info()
                    if info:
                        pct = info.get("percentage", "?")
                        src = info.get("power_source", "?")
                        remaining = info.get("time_remaining", "")
                        icon = "🔌" if src == "AC Power" else "🔋"
                        msg = f"{icon} Battery: {pct}% ({src})"
                        if remaining:
                            msg += f" — {remaining} remaining"
                        successful.append(msg)
                    else:
                        failed.append("❌ Could not get battery info")

                elif action == "wifi":
                    info = macos_sys.get_wifi_info()
                    if info.get("connected"):
                        successful.append(f"📶 WiFi: Connected to **{info['network']}**")
                    else:
                        successful.append("📶 WiFi: Not connected")

                elif action == "lockscreen":
                    macos_sys.lock_screen()
                    successful.append("🔒 Screen locked")

                elif action == "say":
                    macos_sys.text_to_speech(path1)
                    successful.append(f'🗣️ Speaking: "{path1[:50]}"')

                elif action == "eject":
                    if macos_sys.eject_volume(path1):
                        successful.append(f"⏏️ Ejected: {path1}")
                    else:
                        failed.append(f"❌ Could not eject: {path1}")

                elif action == "symlink" and path2:
                    if macos_sys.create_symlink(path1, path2):
                        successful.append(f"🔗 Symlink: `{path2}` → `{path1}`")
                    else:
                        failed.append(f"❌ Could not create symlink")

                elif action == "wallpaper":
                    if macos_sys.set_wallpaper(path1):
                        successful.append(f"🖼️ Wallpaper set: `{path1}`")
                    else:
                        failed.append(f"❌ Could not set wallpaper: `{path1}`")

                elif action == "hiddenfiles":
                    state = macos_sys.toggle_hidden_files()
                    successful.append(f"👻 Hidden files are now **{state}**")

                elif action == "runningapps":
                    apps = macos_sys.get_running_apps()
                    if apps:
                        lines = [f"📱 Running apps ({len(apps)}):"]
                        for a in apps:
                            lines.append(f"  • {a}")
                        successful.append("\n".join(lines))
                    else:
                        successful.append("📱 No running apps found")

                elif action == "foldersize":
                    size = macos_sys.get_folder_size(path1)
                    if size:
                        successful.append(f"📊 `{path1}`: {size}")
                    else:
                        failed.append(f"❌ Could not get size for: `{path1}`")

                elif action == "createrule" and path2:
                    result_msg = self._create_rule_from_chat(path1, path2)
                    if result_msg.startswith("✅"):
                        successful.append(result_msg)
                    else:
                        failed.append(result_msg)

                elif action == "renameai" and path1:
                    from sortmeout.gui.chat_window import _save_ai_name

                    if _save_ai_name(path1):
                        successful.append(
                            f"✅ Assistant renamed to **{path1}** — restart chat to see the change"
                        )
                    else:
                        failed.append("❌ Could not save assistant name")

                else:
                    # ── Integration commands (mail, calendar, messages, etc.) ──
                    integration_result = self._run_integration_command(action, path1, path2)
                    if integration_result is not None:
                        if integration_result.startswith("❌"):
                            failed.append(integration_result)
                        else:
                            successful.append(integration_result)

            except Exception as e:
                failed.append(f"❌ {action} {Path(path1).name if path1 else ''}: {str(e)[:50]}")

        # Remove EXECUTE commands from the AI response
        clean_response = re.sub(self._command_pattern, "", response).strip()
        # Remove leftover blank lines
        clean_response = re.sub(r"\n{3,}", "\n\n", clean_response)

        # Build result report with full paths
        result_lines = []

        if successful or failed:
            result_lines.append("\n\n---")

            if successful:
                result_lines.append(f"\n✅ **{len(successful)} action(s) completed**\n")

            # Grouped path summary for moves/copies
            if moves_by_dest:
                for dest_folder, files in moves_by_dest.items():
                    if len(files) == 1:
                        name, full_path = files[0]
                        result_lines.append(f"- **{name}** → `{full_path}`")
                    else:
                        result_lines.append(f"")
                        result_lines.append(f"**→ `{dest_folder}`** ({len(files)} files)")
                        for name, full_path in files:
                            result_lines.append(f"  - {name}")

            # Non-move actions (system commands, search results, etc.)
            non_move = [
                s for s in successful if not s.startswith("✅ ") and not s.startswith("📋 ")
            ]
            for item in non_move:
                result_lines.append(f"\n{item}")

            if failed:
                result_lines.append(f"")
                result_lines.append(f"⚠️ **{len(failed)} failed:**")
                for f in failed[:5]:
                    result_lines.append(f"  {f}")

            if failed and not successful:
                clean_response = "**No actions could be completed.**\n\n" + clean_response

            if successful:
                self._load_folder_structure()

        return clean_response + "\n".join(result_lines)

    def clear_conversation(self):
        """Clear conversation history."""
        self.conversation_history = []
        self._save_conversation_history()
        return "Conversation history cleared."

    def refresh_knowledge(self):
        """Refresh folder structure knowledge."""
        self._load_folder_structure()
        return {"status": "Folder structure updated", "folders": list(self.folder_structure.keys())}
