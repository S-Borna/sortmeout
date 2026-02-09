"""
macOS Contacts.app integration via AppleScript/JXA.

Capabilities:
    - Search contacts by name, email, phone
    - Get contact details
    - List contact groups
    - Look up a contact for the AI to reference in emails/messages
"""

from __future__ import annotations

import subprocess
import json
from typing import Optional, Dict, List, Any

from sortmeout.utils.logger import get_logger

logger = get_logger(__name__)


class ContactsIntegration:
    """Interface to macOS Contacts.app via JXA."""

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

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search contacts by name, email, or phone number."""
        jxa_script = f"""
        (() => {{
            const Contacts = Application("Contacts");
            const people = Contacts.people();
            const query = "{query}".toLowerCase();
            const results = [];

            for (let i = 0; i < people.length && results.length < {limit}; i++) {{
                const p = people[i];
                try {{
                    const firstName = (p.firstName() || "").toLowerCase();
                    const lastName = (p.lastName() || "").toLowerCase();
                    const fullName = firstName + " " + lastName;
                    const org = (p.organization() || "").toLowerCase();

                    // Check name and organization
                    let match = fullName.includes(query) || org.includes(query);

                    // Check emails
                    const emails = p.emails();
                    const emailList = [];
                    for (let e = 0; e < emails.length; e++) {{
                        const addr = emails[e].value() || "";
                        emailList.push(addr);
                        if (addr.toLowerCase().includes(query)) match = true;
                    }}

                    // Check phones
                    const phones = p.phones();
                    const phoneList = [];
                    for (let ph = 0; ph < phones.length; ph++) {{
                        const num = phones[ph].value() || "";
                        phoneList.push(num);
                        if (num.includes(query)) match = true;
                    }}

                    if (match) {{
                        results.push({{
                            name: (p.firstName() || "") + " " + (p.lastName() || ""),
                            firstName: p.firstName() || "",
                            lastName: p.lastName() || "",
                            organization: p.organization() || "",
                            emails: emailList,
                            phones: phoneList,
                            note: (p.note() || "").substring(0, 200),
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

    def get_contact(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific contact by exact or close name match."""
        results = self.search(name, limit=1)
        return results[0] if results else None

    def get_groups(self) -> List[str]:
        """List all contact groups."""
        jxa_script = """
        (() => {
            const Contacts = Application("Contacts");
            const groups = Contacts.groups();
            return JSON.stringify(groups.map(g => g.name()));
        })()
        """
        result = self._run_jxa(jxa_script)
        if not result:
            return []
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return []

    def get_group_members(self, group_name: str) -> List[Dict[str, Any]]:
        """Get all contacts in a group."""
        jxa_script = f"""
        (() => {{
            const Contacts = Application("Contacts");
            const groups = Contacts.groups.whose({{name: "{group_name}"}})();

            if (groups.length === 0) return JSON.stringify([]);

            const people = groups[0].people();
            return JSON.stringify(people.map(p => ({{
                name: (p.firstName() || "") + " " + (p.lastName() || ""),
                emails: p.emails().map(e => e.value()),
                phones: p.phones().map(ph => ph.value()),
            }})));
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

    def create_contact(
        self,
        first_name: str,
        last_name: str = "",
        phone: str = "",
        email: str = "",
        organization: str = "",
        note: str = "",
    ) -> Dict[str, Any]:
        """Create a new contact in Contacts.app.

        Args:
            first_name: First name (required)
            last_name: Last name (optional)
            phone: Phone number (optional)
            email: Email address (optional)
            organization: Company/organization (optional)
            note: Note text (optional)
        """
        props = [f'first name:"{first_name}"']
        if last_name:
            props.append(f'last name:"{last_name}"')
        if organization:
            props.append(f'organization:"{organization}"')
        if note:
            safe_note = note.replace('"', '\\"')
            props.append(f'note:"{safe_note}"')

        props_str = ", ".join(props)

        phone_block = ""
        if phone:
            phone_block = f"""
            tell newPerson
                make new phone at end of phones with properties {{label:"mobile", value:"{phone}"}}
            end tell
            """

        email_block = ""
        if email:
            email_block = f"""
            tell newPerson
                make new email at end of emails with properties {{label:"home", value:"{email}"}}
            end tell
            """

        script = f"""
        tell application "Contacts"
            set newPerson to make new person with properties {{{props_str}}}
            {phone_block}
            {email_block}
            save
        end tell
        """
        self._run_applescript(script)
        full_name = f"{first_name} {last_name}".strip()
        return {"success": True, "action": "created", "name": full_name}

    def edit_contact(
        self,
        search_name: str,
        new_phone: str = "",
        new_email: str = "",
        new_organization: str = "",
        new_note: str = "",
    ) -> Dict[str, Any]:
        """Edit an existing contact by name.

        Args:
            search_name: Name to search for (finds first match)
            new_phone: New phone number to add (optional)
            new_email: New email to add (optional)
            new_organization: New organization (optional)
            new_note: New note (optional)
        """
        updates = []
        if new_organization:
            updates.append(f'set organization of targetPerson to "{new_organization}"')
        if new_note:
            safe_note = new_note.replace('"', '\\"')
            updates.append(f'set note of targetPerson to "{safe_note}"')

        phone_block = ""
        if new_phone:
            phone_block = f"""
            tell targetPerson
                make new phone at end of phones with properties {{label:"mobile", value:"{new_phone}"}}
            end tell
            """

        email_block = ""
        if new_email:
            email_block = f"""
            tell targetPerson
                make new email at end of emails with properties {{label:"home", value:"{new_email}"}}
            end tell
            """

        updates_str = "\n            ".join(updates)

        script = f"""
        tell application "Contacts"
            set matchingPeople to (every person whose name contains "{search_name}")
            if (count of matchingPeople) > 0 then
                set targetPerson to item 1 of matchingPeople
                {updates_str}
                {phone_block}
                {email_block}
                save
                return "ok"
            else
                return "not found"
            end if
        end tell
        """
        result = self._run_applescript(script)
        if result == "ok":
            return {"success": True, "action": "edited", "name": search_name}
        return {"error": f"Contact '{search_name}' not found"}

    def delete_contact(self, search_name: str) -> Dict[str, Any]:
        """Delete a contact by name.

        Args:
            search_name: Name to search for
        """
        script = f"""
        tell application "Contacts"
            set matchingPeople to (every person whose name contains "{search_name}")
            if (count of matchingPeople) > 0 then
                delete item 1 of matchingPeople
                save
                return "ok"
            else
                return "not found"
            end if
        end tell
        """
        result = self._run_applescript(script)
        if result == "ok":
            return {"success": True, "action": "deleted", "name": search_name}
        return {"error": f"Contact '{search_name}' not found"}
