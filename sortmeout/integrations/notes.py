"""
macOS Notes.app integration via AppleScript/JXA.

Capabilities:
    - List notes
    - Read note content
    - Create new notes
    - Search notes by keyword
    - Append to existing notes
"""

from __future__ import annotations

import subprocess
import json
from typing import Optional, Dict, List, Any

from sortmeout.utils.logger import get_logger

logger = get_logger(__name__)


class NotesIntegration:
    """Interface to macOS Notes.app via AppleScript."""

    def _run_applescript(self, script: str) -> str:
        """Execute AppleScript and return output."""
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode != 0:
                logger.error("AppleScript error: %s", result.stderr.strip())
                return ""
            return result.stdout.strip()
        except Exception as e:
            logger.error("AppleScript failed: %s", e)
            return ""

    def _run_jxa(self, script: str) -> str:
        """Execute JXA and return output."""
        try:
            result = subprocess.run(
                ["osascript", "-l", "JavaScript", "-e", script],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode != 0:
                logger.error("JXA error: %s", result.stderr.strip())
                return ""
            return result.stdout.strip()
        except Exception as e:
            logger.error("JXA failed: %s", e)
            return ""

    def get_recent_notes(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get recent notes with title and preview."""
        jxa_script = f"""
        (() => {{
            const Notes = Application("Notes");
            const notes = Notes.notes();
            const count = Math.min({count}, notes.length);
            const results = [];

            for (let i = 0; i < count; i++) {{
                try {{
                    const n = notes[i];
                    const body = n.plaintext() || "";
                    results.push({{
                        id: n.id(),
                        name: n.name() || "(untitled)",
                        preview: body.substring(0, 200).replace(/\\n/g, " "),
                        creationDate: n.creationDate().toISOString(),
                        modificationDate: n.modificationDate().toISOString(),
                    }});
                }} catch(e) {{}}
            }}

            return JSON.stringify(results);
        }})()
        """
        result = self._run_jxa(jxa_script)
        if not result:
            return []
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return []

    def read_note(self, note_name: str) -> Dict[str, Any]:
        """Read full content of a note by name."""
        jxa_script = f"""
        (() => {{
            const Notes = Application("Notes");
            const notes = Notes.notes.whose({{name: "{note_name}"}})();

            if (notes.length === 0) return JSON.stringify({{error: "Note not found"}});

            const n = notes[0];
            return JSON.stringify({{
                id: n.id(),
                name: n.name(),
                content: n.plaintext() || "",
                creationDate: n.creationDate().toISOString(),
                modificationDate: n.modificationDate().toISOString(),
            }});
        }})()
        """
        result = self._run_jxa(jxa_script)
        if not result:
            return {"error": "Could not read note"}
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"error": "Parse error"}

    def create_note(self, title: str, body: str, folder: Optional[str] = None) -> Dict[str, Any]:
        """Create a new note."""
        safe_title = title.replace('"', '\\"')
        # Notes.app body is HTML — convert newlines to <br>
        safe_body = body.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "<br>")

        if folder:
            safe_folder = folder.replace('"', '\\"')
            script = f"""
            tell application "Notes"
                tell folder "{safe_folder}"
                    make new note with properties {{name:"{safe_title}", body:"{safe_body}"}}
                end tell
            end tell
            """
        else:
            script = f"""
            tell application "Notes"
                make new note with properties {{name:"{safe_title}", body:"{safe_body}"}}
            end tell
            """
        self._run_applescript(script)
        return {"success": True, "title": title, "folder": folder or "default"}

    def search_notes(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search notes by keyword."""
        jxa_script = f"""
        (() => {{
            const Notes = Application("Notes");
            const notes = Notes.notes();
            const query = "{query}".toLowerCase();
            const results = [];

            for (let i = 0; i < notes.length && results.length < {limit}; i++) {{
                try {{
                    const n = notes[i];
                    const name = (n.name() || "").toLowerCase();
                    const body = (n.plaintext() || "").toLowerCase();

                    if (name.includes(query) || body.includes(query)) {{
                        results.push({{
                            id: n.id(),
                            name: n.name() || "(untitled)",
                            preview: (n.plaintext() || "").substring(0, 200),
                            modificationDate: n.modificationDate().toISOString(),
                        }});
                    }}
                }} catch(e) {{}}
            }}

            return JSON.stringify(results);
        }})()
        """
        result = self._run_jxa(jxa_script)
        if not result:
            return []
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return []

    def append_to_note(self, note_name: str, text: str) -> Dict[str, Any]:
        """Append text to an existing note."""
        safe_text = text.replace('"', '\\"').replace("\n", "<br>")

        jxa_script = f"""
        (() => {{
            const Notes = Application("Notes");
            const notes = Notes.notes.whose({{name: "{note_name}"}})();

            if (notes.length === 0) return JSON.stringify({{error: "Note not found"}});

            const n = notes[0];
            const current = n.body();
            n.body = current + "<br><br>{safe_text}";
            return JSON.stringify({{success: true, name: n.name()}});
        }})()
        """
        result = self._run_jxa(jxa_script)
        if not result:
            return {"error": "Could not append to note"}
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"error": "Append failed"}

    def edit_note(self, note_name: str, new_body: str) -> Dict[str, Any]:
        """Replace the full body of an existing note.

        Args:
            note_name: Title of the note to edit
            new_body: New content to replace the existing body
        """
        safe_body = new_body.replace('"', '\\"').replace("\n", "<br>")

        jxa_script = f"""
        (() => {{
            const Notes = Application("Notes");
            const notes = Notes.notes.whose({{name: "{note_name}"}})();

            if (notes.length === 0) return JSON.stringify({{error: "Note not found"}});

            const n = notes[0];
            n.body = "{safe_body}";
            return JSON.stringify({{success: true, name: n.name()}});
        }})()
        """
        result = self._run_jxa(jxa_script)
        if not result:
            return {"error": "Could not edit note"}
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"error": "Edit failed"}

    def delete_note(self, note_name: str) -> Dict[str, Any]:
        """Delete a note by name.

        Args:
            note_name: Title of the note to delete
        """
        script = f"""
        tell application "Notes"
            set matchingNotes to (every note whose name is "{note_name}")
            if (count of matchingNotes) > 0 then
                delete item 1 of matchingNotes
                return "ok"
            else
                return "not found"
            end if
        end tell
        """
        result = self._run_applescript(script)
        if result == "ok":
            return {"success": True, "action": "deleted", "title": note_name}
        return {"error": f"Note '{note_name}' not found"}
