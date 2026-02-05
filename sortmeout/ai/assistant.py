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
        self.conversation_history = []  # Spara konversationshistorik
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
                    # Lägg till filer också (max 50 per mapp för att inte överbelasta)
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
        """Save a history entry."""
        self.file_history.append(entry)
        # Keep last 100 entries
        self.file_history = self.file_history[-100:]

        history_file = os.path.join(self.config_path, "history.json")
        try:
            with open(history_file, "w") as f:
                json.dump(self.file_history, f, indent=2)
        except:
            pass

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

        prompt = f"""Du är en intelligent filassistent för macOS. Användaren har en ny fil och behöver hjälp att organisera den.

FILINFORMATION:
- Namn: {file_info['name']}
- Typ: {file_info['extension']} ({file_info['mime_type']})
- Storlek: {file_info['size_human']}
- Plats nu: {file_info['parent']}

{f"FILINNEHÅLL (förhandsvisning):{chr(10)}{file_info['content_preview'][:500]}" if file_info.get('content_preview') else ""}

ANVÄNDARENS MAPPSTRUKTUR:
{folder_context}

TIDIGARE ORGANISERING (för kontext):
{history_context if history_context else "Ingen historik än"}

{f"ANVÄNDARENS KOMMENTAR: {user_context}" if user_context else ""}

UPPGIFT:
1. Analysera filen baserat på namn, typ och innehåll
2. Föreslå 3-4 lämpliga platser baserat på användarens mappstruktur
3. Ge en rekommendation och förklara varför

Svara på SVENSKA i detta JSON-format:
{{
  "analysis": "Kort analys av vad filen verkar vara",
  "suggestions": [
    {{"path": "~/Documents/...", "reason": "Varför denna plats passar", "confidence": 0.9}},
    {{"path": "~/...", "reason": "...", "confidence": 0.7}}
  ],
  "recommended": 0,
  "additional_actions": ["Byt namn till...", "Skapa undermapp...", etc],
  "question": "Eventuell följdfråga till användaren"
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

            elif action == "copy":
                if not destination:
                    return {"success": False, "error": "Destination required"}

                dest_path = Path(os.path.expanduser(destination))
                dest_path.mkdir(parents=True, exist_ok=True)

                final_dest = dest_path / path.name
                shutil.copy2(str(path), str(final_dest))
                result = {"success": True, "action": "copy", "destination": str(final_dest)}

            elif action == "rename":
                new_name = kwargs.get("new_name")
                if not new_name:
                    return {"success": False, "error": "New name required"}

                new_path = path.parent / new_name
                path.rename(new_path)
                result = {"success": True, "action": "rename", "new_path": str(new_path)}

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

            elif action == "open":
                import subprocess

                subprocess.run(["open", filepath])
                result = {"success": True, "action": "open"}

            # Save to history
            if result.get("success"):
                self._save_history(
                    {
                        "filename": path.name,
                        "action": action,
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

        # FÖRST: Kolla om användaren bekräftar väntande kommandon
        if (
            self._user_has_confirmed(message)
            and hasattr(self, "pending_commands")
            and self.pending_commands
        ):
            num_commands = len(self.pending_commands)
            result = self._execute_pending_commands()
            self.pending_commands = []
            return f"🚀 **Utför {num_commands} åtgärder...**{result}"

        files_context = ""
        if files:
            for f in files:
                info = self.analyze_file(f)
                files_context += f"\nFil: {info.get('name', f)}\n"
                files_context += f"  Typ: {info.get('extension', 'okänd')}\n"
                files_context += f"  Storlek: {info.get('size_human', 'okänd')}\n"

        folder_context = json.dumps(self.folder_structure, indent=2)
        home_dir = os.path.expanduser("~")

        # Hämta detaljerad lista över Downloads-filer
        downloads_files = self.list_files_in_folder("~/Downloads")
        downloads_list = ""
        if downloads_files:
            downloads_list = "\n\nFILER I DOWNLOADS:\n"
            for f in downloads_files:
                ftype = "📁" if f["is_dir"] else "📄"
                downloads_list += f"  {ftype} {f['name']}\n"
        else:
            downloads_list = "\n\nDOWNLOADS: (tom)\n"

        system_prompt = f"""Du är SortMeOut Assistant, en vänlig och intelligent filassistent för macOS.

PERSONLIGHET:
- Var varm, hjälpsam och kommunikativ
- Förklara ditt resonemang - varför du föreslår något
- Ställ följdfrågor för att förstå användarens behov bättre
- Var försiktig med användarens filer - de är viktiga!

KRITISK REGEL - LÄS NOGA:
Du får ALDRIG inkludera [EXECUTE:...] kommandon i ett svar där du också ställer en fråga!
- Om du presenterar en plan och frågar "Vill du att jag utför detta?" = INGA EXECUTE-kommandon
- ENDAST när användaren REDAN har svarat "ja", "kör", "gör det" = då får du använda EXECUTE

ARBETSFLÖDE (följ exakt):
STEG 1 - Första svaret:
- Presentera en detaljerad plan
- Lista varje fil med exakt namn och vart den ska
- Avsluta med: "Vill du att jag genomför detta? (ja/nej)"
- INGA [EXECUTE:] KOMMANDON I DETTA SVAR!

STEG 2 - Efter användaren sagt ja:
- Nu och ENDAST nu får du använda [EXECUTE:] kommandon
- Utför alla åtgärder
- Rapportera vad som gjordes

EXECUTE-KOMMANDON (ENDAST efter bekräftelse):
[EXECUTE: mkdir "{home_dir}/Desktop/Målmapp"]
[EXECUTE: move "{home_dir}/Downloads/EXAKT_FILNAMN" "{home_dir}/Desktop/Målmapp"]
[EXECUTE: copy "källsökväg" "målmapp"]
[EXECUTE: rename "sökväg" "nytt_namn"]
[EXECUTE: trash "sökväg"]

VIKTIGA REGLER FÖR EXECUTE:
- ALDRIG använd wildcard (*) - det fungerar inte
- Använd ALLTID exakta filnamn från fillistan nedan
- En EXECUTE per fil
- Fullständiga sökvägar alltid (börja med {home_dir})

KRITISKT VID EXEKVERING:
- När användaren bekräftat (ja, kör, utför) - skriv ALLA kommandon i ETT svar
- Dela ALDRIG upp i flera meddelanden
- Skriv ALLA mkdir först, sedan ALLA move/copy/etc
- Du har gott om utrymme (8000 tokens) - använd det!
- Avbryt ALDRIG mitt i - kör ALLT till slut

ANVÄNDARENS HEMKATALOG: {home_dir}

ANVÄNDARENS MAPPSTRUKTUR:
{folder_context}
{downloads_list}

{f"FILER SOM DISKUTERAS:{files_context}" if files_context else ""}

VIKTIGT:
- Referera ALLTID till exakta filnamn från listan ovan
- Skapa mappar med mkdir INNAN du flyttar till dem
- Svara ALLTID på svenska
- Var transparent med vad du planerar göra
- Vid osäkerhet - fråga användaren!"""

        # Lägg till användarens meddelande i historiken
        self.conversation_history.append({"role": "user", "content": message})

        # Begränsa historik till senaste 20 meddelanden
        if len(self.conversation_history) > 20:
            self.conversation_history = self.conversation_history[-20:]

        try:
            response = self.client.messages.create(
                model=get_model(),
                max_tokens=8000,  # Ökat för att kunna köra alla kommandon i ett svep
                system=system_prompt,
                messages=self.conversation_history,
            )

            # Record successful AI execution for rate limiting
            record_ai_execution()

            assistant_response = response.content[0].text

            # Spara assistentens svar i historiken
            self.conversation_history.append({"role": "assistant", "content": assistant_response})

            # SÄKERHETSKONTROLL: Kör INTE kommandon om AI:n frågar om bekräftelse
            if self._is_asking_for_confirmation(assistant_response):
                # Spara kommandona för senare, men kör dem inte nu
                self.pending_commands = self._extract_commands(assistant_response)
                # Ta bort EXECUTE-kommandon från svaret så de inte visas
                clean_response = self._remove_execute_commands(assistant_response)
                if self.pending_commands:
                    clean_response += (
                        f"\n\n*({len(self.pending_commands)} åtgärder väntar på bekräftelse)*"
                    )
                return clean_response

            # Utför eventuella kommandon i svaret (om ingen fråga ställs)
            executed_response = self._execute_commands_in_response(assistant_response)

            return executed_response

        except Exception as e:
            return f"Fel vid kommunikation med AI: {str(e)}"

    def _is_asking_for_confirmation(self, response: str) -> bool:
        """Detekterar om AI:n frågar användaren om bekräftelse."""
        confirmation_phrases = [
            "vill du att jag",
            "vill du att jag genomför",
            "(ja/nej)",
            "ja eller nej",
            "bekräfta",
            "ska jag utföra",
            "ska jag genomföra",
            "godkänner du",
            "vill du fortsätta",
        ]
        response_lower = response.lower()
        return any(phrase in response_lower for phrase in confirmation_phrases)

    def _user_has_confirmed(self, message: str) -> bool:
        """Kollar om användarens meddelande är en bekräftelse."""
        confirmations = [
            "ja",
            "yes",
            "kör",
            "gör det",
            "utför",
            "ok",
            "okej",
            "genomför",
            "fortsätt",
            "japp",
            "jepp",
            "absolutely",
            "sure",
        ]
        message_lower = message.lower().strip()
        return message_lower in confirmations or message_lower.startswith("ja ")

    def _extract_commands(self, response: str) -> list:
        """Extraherar EXECUTE-kommandon från svaret utan att köra dem."""
        import re

        pattern = r'\[EXECUTE:\s*(move|copy|rename|mkdir|trash)\s+"([^"]+)"(?:\s+"([^"]+)")?\]'
        return re.findall(pattern, response)

    def _remove_execute_commands(self, response: str) -> str:
        """Tar bort EXECUTE-kommandon från AI:ns svar."""
        import re

        pattern = r'\[EXECUTE:\s*(move|copy|rename|mkdir|trash)\s+"([^"]+)"(?:\s+"([^"]+)")?\]'
        clean = re.sub(pattern, "", response)
        # Ta bort extra tomma rader
        clean = re.sub(r"\n{3,}", "\n\n", clean)
        return clean.strip()

    def _execute_pending_commands(self) -> str:
        """Kör alla väntande kommandon."""
        import shutil
        import os
        from pathlib import Path

        if not hasattr(self, "pending_commands") or not self.pending_commands:
            return "\n\n*Inga väntande kommandon att köra.*"

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
                    else:
                        failed.append(f"❌ {Path(path1).name} (finns ej)")
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
                    else:
                        failed.append(f"❌ {Path(path1).name} (finns ej)")
                elif action == "copy" and path2:
                    src = Path(path1)
                    if src.exists():
                        os.makedirs(path2, exist_ok=True)
                        dest = Path(path2) / src.name
                        shutil.copy2(str(src), str(dest))
                        successful.append(f"📋 {src.name}")
                elif action == "rename" and path2:
                    src = Path(path1)
                    if src.exists():
                        src.rename(src.parent / path2)
                        successful.append(f"✏️ {src.name} → {path2}")
            except Exception as e:
                failed.append(f"❌ {Path(path1).name}: {str(e)[:30]}")

        # Kompakt resultatrapport
        result = "\n\n---\n"
        if successful:
            result += f"✅ **{len(successful)} lyckades**\n"
        if failed:
            result += f"⚠️ **{len(failed)} misslyckades**\n"
            for f in failed[:5]:  # Visa max 5 fel
                result += f"  {f}\n"

        # Uppdatera mappstruktur
        if successful:
            self._load_folder_structure()

        return result

    def _execute_commands_in_response(self, response: str) -> str:
        """Parse and execute [EXECUTE: ...] commands in the response."""
        import re
        import shutil

        # Hitta alla EXECUTE-kommandon
        pattern = r'\[EXECUTE:\s*(move|copy|rename|mkdir|trash)\s+"([^"]+)"(?:\s+"([^"]+)")?\]'
        matches = re.findall(pattern, response)

        if not matches:
            return response  # Inga kommandon att köra

        successful = []
        failed = []

        for match in matches:
            action = match[0]
            path1 = os.path.expanduser(match[1])
            path2 = os.path.expanduser(match[2]) if match[2] else None

            try:
                if action == "mkdir":
                    os.makedirs(path1, exist_ok=True)
                    successful.append(f"✅ Skapade mapp: {Path(path1).name}")

                elif action == "move":
                    if path2:
                        src = Path(path1)
                        if src.exists():
                            os.makedirs(path2, exist_ok=True)
                            dest = Path(path2) / src.name
                            shutil.move(str(src), str(dest))
                            successful.append(f"✅ Flyttade: {src.name} → {Path(path2).name}/")
                            self._save_history(
                                {
                                    "filename": src.name,
                                    "action": "move",
                                    "destination": str(dest),
                                    "timestamp": datetime.now().isoformat(),
                                }
                            )
                        else:
                            failed.append(f"❌ Kunde inte flytta - finns ej: {Path(path1).name}")
                    else:
                        failed.append(f"❌ Ingen destination angiven för: {Path(path1).name}")

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
                            successful.append(f"✅ Kopierade: {src.name} → {Path(path2).name}/")
                        else:
                            failed.append(f"❌ Kunde inte kopiera - finns ej: {Path(path1).name}")

                elif action == "rename":
                    if path2:
                        src = Path(path1)
                        if src.exists():
                            new_path = src.parent / path2
                            src.rename(new_path)
                            successful.append(f"✅ Döpte om: {src.name} → {path2}")
                        else:
                            failed.append(f"❌ Kunde inte döpa om - finns ej: {Path(path1).name}")

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
                        successful.append(f"✅ Slängde i papperskorg: {Path(path1).name}")
                    else:
                        failed.append(f"❌ Kunde inte slänga - finns ej: {Path(path1).name}")

            except Exception as e:
                failed.append(f"❌ Fel vid {action} på {Path(path1).name}: {str(e)}")

        # Ta bort EXECUTE-kommandon från AI:ns svar
        clean_response = re.sub(pattern, "", response).strip()
        # Ta bort tomma rader som blev kvar
        clean_response = re.sub(r"\n{3,}", "\n\n", clean_response)

        # Bygg resultatrapport
        result_lines = []

        if successful or failed:
            result_lines.append("\n\n---")

            if successful:
                result_lines.append(f"📋 **Genomförda åtgärder ({len(successful)}):**")
                result_lines.extend(successful)

            if failed:
                if successful:
                    result_lines.append("")  # Blank rad
                result_lines.append(f"⚠️ **Misslyckades ({len(failed)}):**")
                result_lines.extend(failed)
                result_lines.append("")
                result_lines.append(
                    "*Tips: Kontrollera att filerna/mapparna finns och försök igen.*"
                )

            # Om ALLT misslyckades, lägg till en varning
            if failed and not successful:
                clean_response = "**OBS: Inga åtgärder kunde genomföras.**\n\n" + clean_response

            # Uppdatera mappstrukturen efter ändringar
            if successful:
                self._load_folder_structure()

        return clean_response + "\n".join(result_lines)

    def clear_conversation(self):
        """Clear conversation history."""
        self.conversation_history = []
        return "Konversationshistorik rensad."

    def refresh_knowledge(self):
        """Refresh folder structure knowledge."""
        self._load_folder_structure()
        return {"status": "Mappstruktur uppdaterad", "folders": list(self.folder_structure.keys())}
