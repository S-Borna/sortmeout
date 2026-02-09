"""
macOS Mail.app integration via AppleScript/JXA.

Capabilities:
    - List mailboxes and accounts
    - Read recent/unread emails (subject, sender, date, body preview)
    - Search emails by keyword, sender, date range
    - Compose new emails (draft or send)
    - Reply to emails (with AI-generated response)
    - Mark as read/unread/flagged
    - Get unread count for proactive notifications
"""

from __future__ import annotations

import subprocess
import json
import os
from datetime import datetime
from typing import Optional, Dict, List, Any

from sortmeout.utils.logger import get_logger

logger = get_logger(__name__)


class MailIntegration:
    """Interface to macOS Mail.app via AppleScript."""

    def _run_applescript(self, script: str) -> str:
        """Execute AppleScript and return output."""
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                logger.error("AppleScript error: %s", result.stderr.strip())
                return ""
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            logger.error("AppleScript timed out")
            return ""
        except Exception as e:
            logger.error("AppleScript failed: %s", e)
            return ""

    def _run_jxa(self, script: str) -> str:
        """Execute JXA (JavaScript for Automation) and return output."""
        try:
            result = subprocess.run(
                ["osascript", "-l", "JavaScript", "-e", script],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                logger.error("JXA error: %s", result.stderr.strip())
                return ""
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            logger.error("JXA timed out")
            return ""
        except Exception as e:
            logger.error("JXA failed: %s", e)
            return ""

    # ──────────────────────────────────────────────────────────────
    # READ
    # ──────────────────────────────────────────────────────────────

    def get_unread_count(self) -> int:
        """Get total unread email count across all accounts."""
        script = 'tell application "Mail" to return unread count of inbox'
        result = self._run_applescript(script)
        try:
            return int(result)
        except (ValueError, TypeError):
            return 0

    def get_accounts(self) -> List[str]:
        """List all mail accounts."""
        script = 'tell application "Mail" to return name of every account'
        result = self._run_applescript(script)
        if not result:
            return []
        return [a.strip() for a in result.split(",")]

    def get_mailboxes(self, account: Optional[str] = None) -> List[str]:
        """List mailboxes, optionally filtered by account."""
        if account:
            script = (
                f'tell application "Mail" to return name of every mailbox of account "{account}"'
            )
        else:
            script = 'tell application "Mail" to return name of every mailbox'
        result = self._run_applescript(script)
        if not result:
            return []
        return [m.strip() for m in result.split(",")]

    def get_recent_emails(self, count: int = 10, unread_only: bool = False) -> List[Dict[str, Any]]:
        """Get recent emails from inbox.

        Returns list of dicts with: subject, sender, date, read, id, preview.
        """
        filter_clause = "whose read status is false" if unread_only else ""

        jxa_script = f"""
        (() => {{
            const Mail = Application("Mail");
            const inbox = Mail.inbox();
            let messages = inbox.messages();

            {"messages = messages.filter(m => !m.readStatus());" if unread_only else ""}

            const count = Math.min({count}, messages.length);
            const results = [];

            for (let i = 0; i < count; i++) {{
                const m = messages[i];
                try {{
                    const content = m.content() || "";
                    results.push({{
                        id: m.id(),
                        subject: m.subject() || "(no subject)",
                        sender: m.sender() || "unknown",
                        date: m.dateReceived().toISOString(),
                        read: m.readStatus(),
                        flagged: m.flaggedStatus(),
                        preview: content.substring(0, 300).replace(/\\n/g, " "),
                    }});
                }} catch(e) {{
                    // skip problematic messages
                }}
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

    def read_email(self, message_id: int) -> Dict[str, Any]:
        """Read full email content by message ID."""
        jxa_script = f"""
        (() => {{
            const Mail = Application("Mail");
            const inbox = Mail.inbox();
            const messages = inbox.messages();

            for (let i = 0; i < messages.length; i++) {{
                const m = messages[i];
                if (m.id() === {message_id}) {{
                    return JSON.stringify({{
                        id: m.id(),
                        subject: m.subject() || "(no subject)",
                        sender: m.sender() || "unknown",
                        date: m.dateReceived().toISOString(),
                        read: m.readStatus(),
                        flagged: m.flaggedStatus(),
                        content: m.content() || "",
                        to: m.toRecipients().map(r => r.address()),
                        cc: m.ccRecipients().map(r => r.address()),
                    }});
                }}
            }}
            return JSON.stringify({{error: "Message not found"}});
        }})()
        """
        result = self._run_jxa(jxa_script)
        if not result:
            return {"error": "Could not read email"}
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"error": "Could not parse email"}

    def search_emails(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search emails by keyword in subject and content."""
        jxa_script = f"""
        (() => {{
            const Mail = Application("Mail");
            const inbox = Mail.inbox();
            const messages = inbox.messages();
            const query = "{query}".toLowerCase();
            const results = [];

            for (let i = 0; i < messages.length && results.length < {limit}; i++) {{
                const m = messages[i];
                try {{
                    const subject = (m.subject() || "").toLowerCase();
                    const sender = (m.sender() || "").toLowerCase();
                    const content = (m.content() || "").toLowerCase();

                    if (subject.includes(query) || sender.includes(query) || content.includes(query)) {{
                        results.push({{
                            id: m.id(),
                            subject: m.subject() || "(no subject)",
                            sender: m.sender() || "unknown",
                            date: m.dateReceived().toISOString(),
                            read: m.readStatus(),
                            preview: (m.content() || "").substring(0, 200).replace(/\\n/g, " "),
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

    # ──────────────────────────────────────────────────────────────
    # WRITE
    # ──────────────────────────────────────────────────────────────

    def compose_email(
        self,
        to: str,
        subject: str,
        body: str,
        cc: Optional[str] = None,
        attachment: Optional[str] = None,
        send: bool = False,
    ) -> Dict[str, Any]:
        """Compose a new email. Opens as draft unless send=True.

        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body text
            cc: CC recipient (optional)
            attachment: File path to attach (optional)
            send: Send immediately if True, otherwise open as draft
        """
        cc_block = ""
        if cc:
            cc_block = f"""
            make new cc recipient at end of cc recipients of msg with properties {{address:"{cc}"}}
            """

        attach_block = ""
        if attachment:
            safe_path = attachment.replace('"', '\\"')
            attach_block = f"""
            tell msg
                make new attachment with properties {{file name:(POSIX file "{safe_path}" as alias)}} at after last paragraph
            end tell
            delay 1
            """

        action = "send msg" if send else "set visible of msg to true"

        script = f"""
        tell application "Mail"
            set msg to make new outgoing message with properties {{subject:"{subject}", content:"{body}", visible:true}}
            tell msg
                make new to recipient at end of to recipients with properties {{address:"{to}"}}
                {cc_block}
            end tell
            {attach_block}
            {action}
        end tell
        """
        self._run_applescript(script)
        mode = "sent" if send else "drafted"
        return {
            "success": True,
            "action": mode,
            "to": to,
            "subject": subject,
            "attachment": attachment or None,
        }

    def reply_to_email(
        self, message_id: int, reply_body: str, send: bool = False
    ) -> Dict[str, Any]:
        """Reply to an email by message ID."""
        action = "send reply_msg" if send else "set visible of reply_msg to true"

        jxa_script = f"""
        (() => {{
            const Mail = Application("Mail");
            const inbox = Mail.inbox();
            const messages = inbox.messages();

            for (let i = 0; i < messages.length; i++) {{
                const m = messages[i];
                if (m.id() === {message_id}) {{
                    const reply_msg = Mail.reply(m, {{openingWindow: true, replyToAll: false}});
                    reply_msg.content = `{reply_body}\\n\\n` + reply_msg.content();
                    {"Mail.send(reply_msg);" if send else ""}
                    return JSON.stringify({{success: true, action: "{"sent" if send else "drafted"}"}});
                }}
            }}
            return JSON.stringify({{error: "Message not found"}});
        }})()
        """
        result = self._run_jxa(jxa_script)
        if not result:
            return {"error": "Could not reply"}
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"error": "Reply failed"}

    # ──────────────────────────────────────────────────────────────
    # ACTIONS
    # ──────────────────────────────────────────────────────────────

    def mark_as_read(self, message_id: int) -> bool:
        """Mark an email as read."""
        jxa_script = f"""
        (() => {{
            const Mail = Application("Mail");
            const messages = Mail.inbox().messages();
            for (let i = 0; i < messages.length; i++) {{
                if (messages[i].id() === {message_id}) {{
                    messages[i].readStatus = true;
                    return "ok";
                }}
            }}
            return "not found";
        }})()
        """
        return self._run_jxa(jxa_script) == "ok"

    def mark_as_flagged(self, message_id: int, flagged: bool = True) -> bool:
        """Flag or unflag an email."""
        jxa_script = f"""
        (() => {{
            const Mail = Application("Mail");
            const messages = Mail.inbox().messages();
            for (let i = 0; i < messages.length; i++) {{
                if (messages[i].id() === {message_id}) {{
                    messages[i].flaggedStatus = {"true" if flagged else "false"};
                    return "ok";
                }}
            }}
            return "not found";
        }})()
        """
        return self._run_jxa(jxa_script) == "ok"

    def search_all_mailboxes(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search emails across ALL mailboxes (inbox, sent, archive, etc.).

        Args:
            query: Search keyword
            limit: Max results to return

        Returns:
            List of email dicts with: subject, sender, date, mailbox, preview
        """
        jxa_script = f"""
        (() => {{
            const Mail = Application("Mail");
            const query = "{query}".toLowerCase();
            const results = [];
            const limit = {limit};

            // Search across all accounts and their mailboxes
            const accounts = Mail.accounts();
            const searchBoxes = [];

            // Always include inbox
            searchBoxes.push({{box: Mail.inbox(), name: "Inbox"}});

            // Add sent, archive, trash from each account
            for (let a = 0; a < accounts.length; a++) {{
                try {{
                    const acc = accounts[a];
                    const mailboxes = acc.mailboxes();
                    for (let mb = 0; mb < mailboxes.length; mb++) {{
                        try {{
                            const name = mailboxes[mb].name();
                            const lname = name.toLowerCase();
                            if (lname.includes("sent") || lname.includes("skicka") ||
                                lname.includes("archive") || lname.includes("arkiv") ||
                                lname.includes("all mail") || lname.includes("drafts") ||
                                lname.includes("utkast") || lname.includes("important") ||
                                lname.includes("flagged")) {{
                                searchBoxes.push({{box: mailboxes[mb], name: name}});
                            }}
                        }} catch(e) {{}}
                    }}
                }} catch(e) {{}}
            }}

            for (let b = 0; b < searchBoxes.length && results.length < limit; b++) {{
                try {{
                    const messages = searchBoxes[b].box.messages();
                    const boxName = searchBoxes[b].name;
                    const maxCheck = Math.min(200, messages.length);

                    for (let i = 0; i < maxCheck && results.length < limit; i++) {{
                        try {{
                            const m = messages[i];
                            const subject = (m.subject() || "").toLowerCase();
                            const sender = (m.sender() || "").toLowerCase();
                            const content = (m.content() || "").substring(0, 500).toLowerCase();

                            if (subject.includes(query) || sender.includes(query) || content.includes(query)) {{
                                results.push({{
                                    id: m.id(),
                                    subject: m.subject() || "(no subject)",
                                    sender: m.sender() || "unknown",
                                    date: m.dateReceived().toISOString(),
                                    read: m.readStatus(),
                                    mailbox: boxName,
                                    preview: (m.content() || "").substring(0, 200).replace(/\\n/g, " "),
                                }});
                            }}
                        }} catch(e) {{}}
                    }}
                }} catch(e) {{}}
            }}

            // Sort by date descending
            results.sort((a, b) => new Date(b.date) - new Date(a.date));
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

    def get_summary(self) -> Dict[str, Any]:
        """Get a quick summary of mail status for proactive assistant."""
        unread = self.get_unread_count()
        recent = self.get_recent_emails(count=5, unread_only=True) if unread > 0 else []
        return {
            "unread_count": unread,
            "recent_unread": recent,
            "has_urgent": any(
                any(
                    word in (e.get("subject", "").lower())
                    for word in ["urgent", "asap", "important", "deadline", "action required"]
                )
                for e in recent
            ),
        }
