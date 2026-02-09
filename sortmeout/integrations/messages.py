"""
macOS Messages (iMessage) integration via AppleScript/JXA.

Capabilities:
    - Read recent messages from a chat/contact
    - Send iMessages
    - Get unread message count
    - List recent conversations
    - Search messages by keyword
"""

from __future__ import annotations

import subprocess
import json
from typing import Optional, Dict, List, Any

from sortmeout.utils.logger import get_logger

logger = get_logger(__name__)


class MessagesIntegration:
    """Interface to macOS Messages.app via AppleScript/JXA."""

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
                self._last_result_ok = False
                return ""
            self._last_result_ok = True
            return result.stdout.strip()
        except Exception as e:
            logger.error("AppleScript failed: %s", e)
            self._last_result_ok = False
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

    # ──────────────────────────────────────────────────────────────
    # READ
    # ──────────────────────────────────────────────────────────────

    def get_recent_chats(self, count: int = 10) -> List[Dict[str, Any]]:
        """Get list of recent chat conversations."""
        jxa_script = f"""
        (() => {{
            const Messages = Application("Messages");
            const chats = Messages.chats();
            const count = Math.min({count}, chats.length);
            const results = [];

            for (let i = 0; i < count; i++) {{
                try {{
                    const chat = chats[i];
                    const participants = chat.participants();
                    const names = participants.map(p => {{
                        try {{ return p.name() || p.handle(); }}
                        catch(e) {{ return "unknown"; }}
                    }});

                    results.push({{
                        id: chat.id(),
                        participants: names,
                        serviceName: chat.serviceName() || "iMessage",
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

    def send_message(self, to: str, text: str) -> Dict[str, Any]:
        """Send an iMessage to a phone number or email.

        Args:
            to: Phone number (e.g. "+46701234567") or email
            text: Message text

        Returns:
            Dict with success status.

        Note: This opens Messages.app and sends. The user should
              have the contact in their Messages already.
        """
        # Escape quotes in text
        safe_text = text.replace("\\", "\\\\").replace('"', '\\"')
        safe_to = to.replace('"', '\\"')

        # Modern AppleScript syntax that works on macOS Monterey+
        script = f"""
        tell application "Messages"
            set targetService to 1st account whose service type = iMessage
            set targetBuddy to buddy "{safe_to}" of targetService
            send "{safe_text}" to targetBuddy
        end tell
        """
        result = self._run_applescript(script)
        if result == "" and not self._last_success:
            return {
                "success": False,
                "error": f"Failed to send message to {to}. Ensure the contact exists in Messages.app and iMessage is signed in.",
            }
        return {"success": True, "to": to, "message": text[:50] + "..." if len(text) > 50 else text}

    @property
    def _last_success(self) -> bool:
        """Check if last AppleScript succeeded (helper)."""
        return getattr(self, "_last_result_ok", True)

    def send_to_chat(self, chat_id: str, text: str) -> Dict[str, Any]:
        """Send a message to an existing chat by chat ID."""
        safe_text = text.replace('"', '\\"')

        script = f"""
        tell application "Messages"
            set targetChat to chat id "{chat_id}"
            send "{safe_text}" to targetChat
        end tell
        """
        self._run_applescript(script)
        return {"success": True, "chat_id": chat_id, "message": text[:50]}

    def read_messages(
        self, chat_id: str = "", contact: str = "", count: int = 10
    ) -> List[Dict[str, Any]]:
        """Read recent messages from a specific chat or contact.

        Uses the Messages SQLite database for reliable message reading.

        Args:
            chat_id: Chat ID to read from (optional)
            contact: Contact phone/email to find chat for (optional)
            count: Number of messages to retrieve

        Returns:
            List of message dicts with: text, sender, date, is_from_me
        """
        import sqlite3
        import os
        from datetime import datetime, timezone

        db_path = os.path.expanduser("~/Library/Messages/chat.db")
        if not os.path.exists(db_path):
            return []

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            if contact:
                # Find chat by contact identifier (phone or email)
                cursor.execute(
                    """
                    SELECT DISTINCT cm.chat_id
                    FROM chat_message_join cm
                    JOIN chat c ON c.ROWID = cm.chat_id
                    JOIN chat_handle_join chj ON chj.chat_id = c.ROWID
                    JOIN handle h ON h.ROWID = chj.handle_id
                    WHERE h.id LIKE ?
                    ORDER BY cm.message_id DESC
                    LIMIT 1
                """,
                    (f"%{contact}%",),
                )
                row = cursor.fetchone()
                if not row:
                    conn.close()
                    return []
                db_chat_id = row[0]
            elif chat_id:
                # Map Messages.app chat_id to DB ROWID
                cursor.execute("SELECT ROWID FROM chat WHERE guid LIKE ?", (f"%{chat_id}%",))
                row = cursor.fetchone()
                if not row:
                    conn.close()
                    return []
                db_chat_id = row[0]
            else:
                # Get most recent chat
                cursor.execute(
                    """
                    SELECT chat_id FROM chat_message_join
                    ORDER BY message_id DESC LIMIT 1
                """
                )
                row = cursor.fetchone()
                if not row:
                    conn.close()
                    return []
                db_chat_id = row[0]

            # Get messages from chat
            cursor.execute(
                """
                SELECT
                    m.text,
                    m.is_from_me,
                    m.date,
                    COALESCE(h.id, 'me') as sender
                FROM message m
                JOIN chat_message_join cmj ON cmj.message_id = m.ROWID
                LEFT JOIN handle h ON h.ROWID = m.handle_id
                WHERE cmj.chat_id = ?
                    AND m.text IS NOT NULL
                    AND m.text != ''
                ORDER BY m.date DESC
                LIMIT ?
            """,
                (db_chat_id, count),
            )

            messages = []
            for row in cursor.fetchall():
                text, is_from_me, date_val, sender = row
                # Convert macOS epoch (2001-01-01) to datetime
                if date_val:
                    # Messages DB uses nanoseconds since 2001-01-01
                    mac_epoch = datetime(2001, 1, 1, tzinfo=timezone.utc)
                    ts = date_val / 1_000_000_000 if date_val > 1_000_000_000_000 else date_val
                    msg_time = datetime.fromtimestamp(mac_epoch.timestamp() + ts)
                    date_str = msg_time.strftime("%Y-%m-%d %H:%M")
                else:
                    date_str = ""

                messages.append(
                    {
                        "text": text,
                        "sender": "me" if is_from_me else sender,
                        "is_from_me": bool(is_from_me),
                        "date": date_str,
                    }
                )

            conn.close()
            # Return in chronological order
            messages.reverse()
            return messages

        except Exception as e:
            logger.error("Failed to read messages: %s", e)
            return []

    def get_summary(self) -> Dict[str, Any]:
        """Get messages summary for proactive assistant."""
        chats = self.get_recent_chats(5)
        return {
            "recent_chats": len(chats),
            "conversations": chats,
        }

    def get_contacts(self) -> List[Dict[str, Any]]:
        """Auto-detect iMessage contacts from the Messages database.

        Reads chat.db to find all unique contacts that the user has
        exchanged messages with. Falls back to Contacts.app if DB unavailable.
        """
        import sqlite3
        import os

        db_path = os.path.expanduser("~/Library/Messages/chat.db")
        if not os.path.exists(db_path):
            logger.warning("Messages database not found. Full Disk Access may be required.")
            return self._get_contacts_from_app()

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Get all handles (contacts) from the messages database
            cursor.execute(
                """
                SELECT DISTINCT
                    h.id,
                    h.service,
                    COALESCE(h.uncanonicalized_id, h.id) as display_id,
                    (SELECT COUNT(*) FROM message m
                     JOIN chat_message_join cmj ON cmj.message_id = m.ROWID
                     JOIN chat_handle_join chj ON chj.chat_id = cmj.chat_id
                     WHERE chj.handle_id = h.ROWID) as msg_count,
                    (SELECT MAX(m.date) FROM message m
                     JOIN chat_message_join cmj ON cmj.message_id = m.ROWID
                     JOIN chat_handle_join chj ON chj.chat_id = cmj.chat_id
                     WHERE chj.handle_id = h.ROWID) as last_msg
                FROM handle h
                WHERE h.service = 'iMessage' OR h.service = 'SMS'
                ORDER BY last_msg DESC
                LIMIT 100
            """
            )

            contacts = []
            for row in cursor.fetchall():
                handle_id, service, display_id, msg_count, _ = row
                contacts.append(
                    {
                        "id": handle_id,
                        "name": display_id,
                        "service": service or "iMessage",
                        "message_count": msg_count or 0,
                    }
                )

            conn.close()
            return contacts

        except Exception as e:
            logger.error("Failed to read contacts from Messages DB: %s", e)
            logger.info("The app may need Full Disk Access permission.")
            return self._get_contacts_from_app()

    def _get_contacts_from_app(self) -> List[Dict[str, Any]]:
        """Fallback: get recently messaged contacts via Messages.app JXA."""
        jxa_script = """
        (() => {
            const Messages = Application("Messages");
            const buddies = Messages.buddies();
            const results = [];

            for (let i = 0; i < Math.min(buddies.length, 50); i++) {
                try {
                    const b = buddies[i];
                    results.push({
                        id: b.handle(),
                        name: b.name() || b.handle(),
                        service: b.serviceName() || "iMessage",
                    });
                } catch(e) {}
            }

            return JSON.stringify(results);
        })()
        """
        result = self._run_jxa(jxa_script)
        if not result:
            return []
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return []

    def check_permissions(self) -> Dict[str, Any]:
        """Check if the app has the necessary permissions for Messages."""
        import os

        db_path = os.path.expanduser("~/Library/Messages/chat.db")

        can_read_db = os.path.exists(db_path) and os.access(db_path, os.R_OK)

        return {
            "database_accessible": can_read_db,
            "messages_app_available": True,
            "note": (
                "Full Disk Access required for reading messages. "
                "Go to System Settings → Privacy & Security → Full Disk Access "
                "and add SortMeOut."
                if not can_read_db
                else "All permissions OK."
            ),
        }
