"""
AI File Assistant powered by Claude API.
Analyzes files and helps organize them intelligently.
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

# Model selection - Haiku for all users, Sonnet only for Creator
MODEL_HAIKU = "claude-3-5-haiku-20241022"  # All users
MODEL_SONNET = "claude-sonnet-4-5-20250929"  # Creator only


def get_model() -> str:
    """Get appropriate model based on license state."""
    license = get_license()
    # Only Creator gets Sonnet
    if license._pro_license_key and "CREATOR" in license._pro_license_key:
        return MODEL_SONNET
    return MODEL_HAIKU  # Everyone else gets Haiku


try:
    import anthropic

    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


class FileAssistant:
    """AI-powered file organization assistant using Claude."""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the assistant with Claude API."""
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")

        if not self.api_key:
            raise ValueError("Claude API key required. Set ANTHROPIC_API_KEY or pass api_key.")

        if not HAS_ANTHROPIC:
            raise ImportError("anthropic package required. Run: pip install anthropic")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.folder_structure = {}
        self.file_history = []
        self.conversation_history = []  # Store conversation history
        self.config_path = os.path.expanduser("~/.config/sortmeout")

        # Load knowledge
        self._load_folder_structure()
        self._load_history()

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

    def chat(self, message: str, files: List[str] = None) -> str:
        """General chat with the assistant about files. Maintains conversation history."""

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

        system_prompt = f"""You are SortMeOut Assistant, a friendly and intelligent file assistant for macOS.

PERSONALITY:
- Be warm, helpful, and communicative
- Explain your reasoning — why you suggest something
- Ask follow-up questions to better understand the user's needs
- Be careful with the user's files — they are important!

CRITICAL RULE — READ CAREFULLY:
You must NEVER include [EXECUTE:...] commands in a response where you also ask a question!
- If you present a plan and ask "Would you like me to do this?" = NO EXECUTE commands
- ONLY when the user has ALREADY replied "yes", "go ahead", "do it" = then you may use EXECUTE

WORKFLOW (follow exactly):
STEP 1 - First response:
- Present a detailed plan
- List each file with its exact name and where it should go
- End with: "Would you like me to proceed? (yes/no)"
- NO [EXECUTE:] COMMANDS IN THIS RESPONSE!

STEP 2 - After the user says yes:
- Now and ONLY now may you use [EXECUTE:] commands
- Execute all actions
- Report what was done

EXECUTE COMMANDS (ONLY after confirmation):
[EXECUTE: mkdir "{home_dir}/Desktop/TargetFolder"]
[EXECUTE: move "{home_dir}/Downloads/EXACT_FILENAME" "{home_dir}/Desktop/TargetFolder"]
[EXECUTE: copy "source_path" "target_folder"]
[EXECUTE: rename "path" "new_name"]
[EXECUTE: trash "path"]

IMPORTANT RULES FOR EXECUTE:
- NEVER use wildcards (*) — they don't work
- ALWAYS use exact filenames from the file list below
- One EXECUTE per file
- Always use full paths (starting with {home_dir})

CRITICAL FOR EXECUTION:
- When the user confirms (yes, go ahead, do it) — write ALL commands in ONE response
- NEVER split across multiple messages
- Write ALL mkdir commands first, then ALL move/copy/etc
- You have plenty of space (8000 tokens) — use it!
- NEVER break off mid-way — execute EVERYTHING to completion

USER'S HOME DIRECTORY: {home_dir}

USER'S FOLDER STRUCTURE:
{folder_context}
{downloads_list}

{f"FILES BEING DISCUSSED:{files_context}" if files_context else ""}

IMPORTANT:
- ALWAYS reference exact filenames from the list above
- Create folders with mkdir BEFORE moving files to them
- Always respond in English
- Be transparent about what you plan to do
- When in doubt — ask the user!"""

        # Add the user's message to history
        self.conversation_history.append({"role": "user", "content": message})

        # Limit history to last 20 messages
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]

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

    def _extract_commands(self, response: str) -> list:
        """Extract EXECUTE commands from the response without running them."""
        import re

        pattern = r'\[EXECUTE:\s*(move|copy|rename|mkdir|trash)\s+"([^"]+)"(?:\s+"([^"]+)")?\]'
        return re.findall(pattern, response)

    def _remove_execute_commands(self, response: str) -> str:
        """Remove EXECUTE commands from the AI response."""
        import re

        pattern = r'\[EXECUTE:\s*(move|copy|rename|mkdir|trash)\s+"([^"]+)"(?:\s+"([^"]+)")?\]'
        clean = re.sub(pattern, "", response)
        # Remove extra blank lines
        clean = re.sub(r"\n{3,}", "\n\n", clean)
        return clean.strip()

    def _execute_pending_commands(self) -> str:
        """Execute all pending commands."""
        import shutil
        import os
        from pathlib import Path

        if not hasattr(self, "pending_commands") or not self.pending_commands:
            return "\n\n*No pending commands to execute.*"

        successful = []
        failed = []

        for match in self.pending_commands:
            action = match[0]
            path1 = os.path.expanduser(match[1])
            path2 = os.path.expanduser(match[2]) if match[2] else None

            try:
                if action == "mkdir":
                    os.makedirs(path1, exist_ok=True)
                    successful.append(f"📁 {Path(path1).name}")
                elif action == "move" and path2:
                    src = Path(path1)
                    if src.exists():
                        os.makedirs(path2, exist_ok=True)
                        dest = Path(path2) / src.name
                        shutil.move(str(src), str(dest))
                        successful.append(f"📦 {src.name}")
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
                        successful.append(f"📋 {src.name}")
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
                        src.rename(src.parent / path2)
                        successful.append(f"✏️ {src.name} → {path2}")
                        get_history().record(
                            action_type="rename",
                            source_path=str(src),
                            destination_path=str(src.parent / path2),
                            rule_name="AI Assistant",
                            metadata={"via": "ai_pending_cmd"},
                        )
            except Exception as e:
                failed.append(f"❌ {Path(path1).name}: {str(e)[:30]}")

        # Compact result report
        result = "\n\n---\n"
        if successful:
            result += f"✅ **{len(successful)} succeeded**\n"
        if failed:
            result += f"⚠️ **{len(failed)} failed**\n"
            for f in failed[:5]:  # Show max 5 errors
                result += f"  {f}\n"

        # Refresh folder structure
        if successful:
            self._load_folder_structure()

        return result

    def _execute_commands_in_response(self, response: str) -> str:
        """Parse and execute [EXECUTE: ...] commands in the response."""
        import re
        import shutil

        # Find all EXECUTE commands
        pattern = r'\[EXECUTE:\s*(move|copy|rename|mkdir|trash)\s+"([^"]+)"(?:\s+"([^"]+)")?\]'
        matches = re.findall(pattern, response)

        if not matches:
            return response  # No commands to run

        successful = []
        failed = []

        for match in matches:
            action = match[0]
            path1 = os.path.expanduser(match[1])
            path2 = os.path.expanduser(match[2]) if match[2] else None

            try:
                if action == "mkdir":
                    os.makedirs(path1, exist_ok=True)
                    successful.append(f"✅ Created folder: {Path(path1).name}")

                elif action == "move":
                    if path2:
                        src = Path(path1)
                        if src.exists():
                            os.makedirs(path2, exist_ok=True)
                            dest = Path(path2) / src.name
                            shutil.move(str(src), str(dest))
                            successful.append(f"✅ Moved: {src.name} → {Path(path2).name}/")
                            get_history().record(
                                action_type="move",
                                source_path=str(src),
                                destination_path=str(dest),
                                rule_name="AI Assistant",
                                metadata={"via": "ai_chat_cmd"},
                            )
                        else:
                            failed.append(f"❌ Could not move — not found: {Path(path1).name}")
                    else:
                        failed.append(f"❌ No destination specified for: {Path(path1).name}")

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
                            successful.append(f"✅ Copied: {src.name} → {Path(path2).name}/")
                            get_history().record(
                                action_type="copy",
                                source_path=str(src),
                                destination_path=str(dest),
                                rule_name="AI Assistant",
                                metadata={"via": "ai_chat_cmd"},
                            )
                        else:
                            failed.append(f"❌ Could not copy — not found: {Path(path1).name}")

                elif action == "rename":
                    if path2:
                        src = Path(path1)
                        if src.exists():
                            new_path = src.parent / path2
                            src.rename(new_path)
                            successful.append(f"✅ Renamed: {src.name} → {path2}")
                            get_history().record(
                                action_type="rename",
                                source_path=str(src),
                                destination_path=str(new_path),
                                rule_name="AI Assistant",
                                metadata={"via": "ai_chat_cmd"},
                            )
                        else:
                            failed.append(f"❌ Could not rename — not found: {Path(path1).name}")

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
                        successful.append(f"✅ Moved to Trash: {Path(path1).name}")
                        get_history().record(
                            action_type="trash",
                            source_path=path1,
                            rule_name="AI Assistant",
                            metadata={"via": "ai_chat_cmd"},
                        )
                    else:
                        failed.append(f"❌ Could not trash — not found: {Path(path1).name}")

            except Exception as e:
                failed.append(f"❌ Error during {action} on {Path(path1).name}: {str(e)}")

        # Remove EXECUTE commands from the AI response
        clean_response = re.sub(pattern, "", response).strip()
        # Remove leftover blank lines
        clean_response = re.sub(r"\n{3,}", "\n\n", clean_response)

        # Build result report
        result_lines = []

        if successful or failed:
            result_lines.append("\n\n---")

            if successful:
                result_lines.append(f"📋 **Actions completed ({len(successful)}):**")
                result_lines.extend(successful)

            if failed:
                if successful:
                    result_lines.append("")  # Blank line
                result_lines.append(f"⚠️ **Failed ({len(failed)}):**")
                result_lines.extend(failed)
                result_lines.append("")
                result_lines.append(
                    "*Tip: Check that the files/folders exist and try again.*"
                )

            # If EVERYTHING failed, add a warning
            if failed and not successful:
                clean_response = "**NOTE: No actions could be completed.**\n\n" + clean_response

            # Refresh folder structure after changes
            if successful:
                self._load_folder_structure()

        return clean_response + "\n".join(result_lines)

    def clear_conversation(self):
        """Clear conversation history."""
        self.conversation_history = []
        return "Conversation history cleared."

    def refresh_knowledge(self):
        """Refresh folder structure knowledge."""
        self._load_folder_structure()
        return {"status": "Folder structure updated", "folders": list(self.folder_structure.keys())}
