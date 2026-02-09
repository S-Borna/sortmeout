"""
SortMeOut Desktop — Python Bridge Handler

Routes all actions from the JavaScript frontend to the appropriate
Python backend modules and returns results as dicts.

Every action handler receives a `payload` dict and returns a `dict`.
Errors are caught at the top level and returned as error messages.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def handle_bridge_action(action: str, payload: dict) -> dict:
    """
    Central action dispatcher — called from BridgeHandler in app.py.

    Args:
        action: Action name from JS (e.g. "chat_send", "email_list")
        payload: Data from JS

    Returns:
        Dict to be sent back to JS as the response.
    """
    handler = _HANDLERS.get(action)
    if not handler:
        return {"error": f"Unknown action: {action}"}

    try:
        return handler(payload)
    except Exception as e:
        logger.error("Bridge action '%s' failed: %s", action, e, exc_info=True)
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════════════════════════════
# HANDLER IMPLEMENTATIONS
# ═══════════════════════════════════════════════════════════════════════════════


# ── Lazy integration singletons ──

_integrations: dict[str, Any] = {}


def _get(name: str):
    """Lazy-load integration modules."""
    if name not in _integrations:
        if name == "mail":
            from sortmeout.integrations.mail import MailIntegration
            _integrations[name] = MailIntegration()
        elif name == "calendar":
            from sortmeout.integrations.calendar import CalendarIntegration
            _integrations[name] = CalendarIntegration()
        elif name == "messages":
            from sortmeout.integrations.messages import MessagesIntegration
            _integrations[name] = MessagesIntegration()
        elif name == "contacts":
            from sortmeout.integrations.contacts import ContactsIntegration
            _integrations[name] = ContactsIntegration()
        elif name == "notes":
            from sortmeout.integrations.notes import NotesIntegration
            _integrations[name] = NotesIntegration()
        elif name == "presentations":
            from sortmeout.integrations.presentations import PresentationBuilder
            _integrations[name] = PresentationBuilder()
        elif name == "images":
            from sortmeout.integrations.images import get_generator, get_editor
            _integrations["image_gen"] = get_generator()
            _integrations["image_edit"] = get_editor()
            _integrations[name] = True
        elif name == "assistant":
            from sortmeout.ai.assistant import Assistant
            _integrations[name] = Assistant()
        elif name == "engine":
            from sortmeout.core.engine import OrganizationEngine
            _integrations[name] = OrganizationEngine()
    return _integrations.get(name)


# ─────────────────────────────────────────────────────────────────────────────
# CHAT
# ─────────────────────────────────────────────────────────────────────────────

def _chat_send(payload: dict) -> dict:
    """Send a message to the AI assistant and get a response."""
    message = payload.get("message", "")
    if not message:
        return {"error": "Empty message"}

    assistant = _get("assistant")
    if not assistant:
        return {"response": "AI assistant is not configured. Please set your API key in Settings."}

    try:
        response = assistant.chat(message)
        return {"response": response}
    except Exception as e:
        return {"response": f"AI error: {e}"}


def _chat_clear(payload: dict) -> dict:
    """Clear chat history."""
    assistant = _get("assistant")
    if assistant and hasattr(assistant, "clear_history"):
        assistant.clear_history()
    elif assistant and hasattr(assistant, "conversation_history"):
        assistant.conversation_history = []
    return {"success": True}


def _chat_history(payload: dict) -> dict:
    """Get chat history."""
    assistant = _get("assistant")
    if assistant and hasattr(assistant, "conversation_history"):
        return {"messages": assistant.conversation_history}
    return {"messages": []}


# ─────────────────────────────────────────────────────────────────────────────
# EMAIL
# ─────────────────────────────────────────────────────────────────────────────

def _email_list(payload: dict) -> dict:
    mail = _get("mail")
    mailbox = payload.get("mailbox", "inbox")
    account = payload.get("account")
    count = payload.get("count", 20)
    try:
        emails = mail.read_emails(mailbox=mailbox, account=account, count=count)
        return {"emails": emails if isinstance(emails, list) else []}
    except Exception as e:
        return {"emails": [], "error": str(e)}


def _email_compose(payload: dict) -> dict:
    mail = _get("mail")
    result = mail.compose_email(
        to=payload.get("to", ""),
        subject=payload.get("subject", ""),
        body=payload.get("body", ""),
        attachment=payload.get("attachment"),
    )
    return {"success": True, "result": str(result)}


def _email_reply(payload: dict) -> dict:
    mail = _get("mail")
    result = mail.reply_to_email(
        to=payload.get("to", ""),
        subject=payload.get("subject", ""),
        body=payload.get("body", ""),
    )
    return {"success": True, "result": str(result)}


def _email_search(payload: dict) -> dict:
    mail = _get("mail")
    query = payload.get("query", "")
    results = mail.search_emails(query)
    return {"emails": results if isinstance(results, list) else []}


def _email_search_all(payload: dict) -> dict:
    mail = _get("mail")
    query = payload.get("query", "")
    results = mail.search_all_mailboxes(query)
    return {"emails": results if isinstance(results, list) else []}


def _email_unread(payload: dict) -> dict:
    mail = _get("mail")
    account = payload.get("account")
    try:
        count = mail.get_unread_count(account=account)
        return {"count": count}
    except Exception as e:
        return {"count": 0, "error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# MESSAGES
# ─────────────────────────────────────────────────────────────────────────────

def _msg_send(payload: dict) -> dict:
    msg = _get("messages")
    result = msg.send_message(
        to=payload.get("to", ""),
        body=payload.get("body", ""),
    )
    return {"success": True, "result": str(result)}


def _msg_read(payload: dict) -> dict:
    msg = _get("messages")
    contact = payload.get("contact", "")
    count = payload.get("count", 20)
    messages = msg.read_messages(contact=contact, count=count)
    return {"messages": messages if isinstance(messages, list) else []}


# ─────────────────────────────────────────────────────────────────────────────
# CALENDAR
# ─────────────────────────────────────────────────────────────────────────────

def _cal_events(payload: dict) -> dict:
    cal = _get("calendar")
    days = payload.get("days", 7)
    events = cal.get_events(days=days)
    return {"events": events if isinstance(events, list) else []}


def _cal_create(payload: dict) -> dict:
    cal = _get("calendar")
    result = cal.create_event(
        title=payload.get("title", ""),
        start_date=payload.get("start_date", ""),
        end_date=payload.get("end_date", ""),
        location=payload.get("location", ""),
        notes=payload.get("notes", ""),
    )
    return {"success": True, "result": str(result)}


def _cal_edit(payload: dict) -> dict:
    cal = _get("calendar")
    result = cal.edit_event(
        title=payload.get("title", ""),
        new_title=payload.get("new_title"),
        new_start=payload.get("new_start"),
        new_end=payload.get("new_end"),
        new_location=payload.get("new_location"),
        new_notes=payload.get("new_notes"),
    )
    return {"success": True, "result": str(result)}


def _cal_delete(payload: dict) -> dict:
    cal = _get("calendar")
    result = cal.delete_event(title=payload.get("title", ""))
    return {"success": True, "result": str(result)}


# ─────────────────────────────────────────────────────────────────────────────
# CONTACTS
# ─────────────────────────────────────────────────────────────────────────────

def _contacts_search(payload: dict) -> dict:
    contacts = _get("contacts")
    query = payload.get("query", "")
    try:
        results = contacts.search_contacts(query) if query else contacts.search_contacts("")
        return {"contacts": results if isinstance(results, list) else []}
    except Exception as e:
        return {"contacts": [], "error": str(e)}


def _contacts_create(payload: dict) -> dict:
    contacts = _get("contacts")
    result = contacts.create_contact(
        first_name=payload.get("first_name", ""),
        last_name=payload.get("last_name", ""),
        phone=payload.get("phone"),
        email=payload.get("email"),
        organization=payload.get("organization"),
        note=payload.get("note"),
    )
    return {"success": True, "result": str(result)}


def _contacts_edit(payload: dict) -> dict:
    contacts = _get("contacts")
    result = contacts.edit_contact(
        name=payload.get("name", ""),
        add_phone=payload.get("add_phone"),
        add_email=payload.get("add_email"),
        new_organization=payload.get("new_organization"),
        new_note=payload.get("new_note"),
    )
    return {"success": True, "result": str(result)}


def _contacts_delete(payload: dict) -> dict:
    contacts = _get("contacts")
    result = contacts.delete_contact(name=payload.get("name", ""))
    return {"success": True, "result": str(result)}


# ─────────────────────────────────────────────────────────────────────────────
# NOTES
# ─────────────────────────────────────────────────────────────────────────────

def _notes_list(payload: dict) -> dict:
    notes = _get("notes")
    folder = payload.get("folder")
    try:
        result = notes.list_notes(folder=folder)
        return {"notes": result if isinstance(result, list) else []}
    except Exception as e:
        return {"notes": [], "error": str(e)}


def _notes_create(payload: dict) -> dict:
    notes = _get("notes")
    result = notes.create_note(
        title=payload.get("title", ""),
        body=payload.get("body", ""),
        folder=payload.get("folder"),
    )
    return {"success": True, "result": str(result)}


def _notes_search(payload: dict) -> dict:
    notes = _get("notes")
    query = payload.get("query", "")
    result = notes.search_notes(query)
    return {"notes": result if isinstance(result, list) else []}


def _notes_edit(payload: dict) -> dict:
    notes = _get("notes")
    result = notes.edit_note(
        title=payload.get("title", ""),
        new_body=payload.get("body", ""),
    )
    return {"success": True, "result": str(result)}


def _notes_delete(payload: dict) -> dict:
    notes = _get("notes")
    result = notes.delete_note(title=payload.get("title", ""))
    return {"success": True, "result": str(result)}


# ─────────────────────────────────────────────────────────────────────────────
# PRESENTATIONS
# ─────────────────────────────────────────────────────────────────────────────

def _pres_create(payload: dict) -> dict:
    pres = _get("presentations")
    title = payload.get("title", "Untitled")
    slides = payload.get("slides", [])
    result = pres.create_presentation(title=title, slides=slides)
    return {"success": True, "result": str(result)}


def _pres_add_slide(payload: dict) -> dict:
    pres = _get("presentations")
    result = pres.add_slide(
        file=payload.get("file", ""),
        title=payload.get("title", ""),
        body=payload.get("body", ""),
    )
    return {"success": True, "result": str(result)}


# ─────────────────────────────────────────────────────────────────────────────
# IMAGES
# ─────────────────────────────────────────────────────────────────────────────

def _img_generate(payload: dict) -> dict:
    _get("images")
    gen = _integrations.get("image_gen")
    if not gen:
        return {"error": "Image generator not available"}

    result = gen.generate(
        prompt=payload.get("prompt", ""),
        size=payload.get("size", "1024x1024"),
        quality=payload.get("quality", "hd"),
        style=payload.get("style", "vivid"),
    )
    return {"success": True, "path": str(result) if result else None}


def _img_edit(payload: dict) -> dict:
    _get("images")
    editor = _integrations.get("image_edit")
    if not editor:
        return {"error": "Image editor not available"}

    path = payload.get("path", "")
    operations = payload.get("operations", [])
    result = editor.process(path, operations)
    return {"success": True, "path": str(result) if result else None}


def _img_gallery(payload: dict) -> dict:
    """List generated images from the default output directory."""
    output_dir = Path.home() / "Pictures" / "SortMeOut"
    images = []
    if output_dir.exists():
        for f in sorted(output_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if f.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}:
                images.append({
                    "path": str(f),
                    "name": f.name,
                    "size": f.stat().st_size,
                    "modified": f.stat().st_mtime,
                })
    return {"images": images[:50]}


# ─────────────────────────────────────────────────────────────────────────────
# RULES / AUTOMATION
# ─────────────────────────────────────────────────────────────────────────────

def _rules_list(payload: dict) -> dict:
    try:
        from sortmeout.config import manager as cfg_manager
        config = cfg_manager.load_config()
        rules = config.get("rules", [])
        return {"rules": rules}
    except Exception as e:
        return {"rules": [], "error": str(e)}


def _rules_create(payload: dict) -> dict:
    # Delegate complex rule creation to the AI assistant
    return {"success": True, "message": "Use AI assistant to create rules"}


def _rules_delete(payload: dict) -> dict:
    try:
        from sortmeout.config import manager as cfg_manager
        config = cfg_manager.load_config()
        name = payload.get("name", "")
        config["rules"] = [r for r in config.get("rules", []) if r.get("name") != name]
        cfg_manager.save_config(config)
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


def _rules_toggle(payload: dict) -> dict:
    try:
        from sortmeout.config import manager as cfg_manager
        config = cfg_manager.load_config()
        name = payload.get("name", "")
        enabled = payload.get("enabled", True)
        for r in config.get("rules", []):
            if r.get("name") == name:
                r["enabled"] = enabled
                break
        cfg_manager.save_config(config)
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# FILES
# ─────────────────────────────────────────────────────────────────────────────

def _files_list(payload: dict) -> dict:
    path = payload.get("path", str(Path.home()))
    p = Path(path)
    if not p.exists():
        return {"files": [], "error": "Path not found"}

    files = []
    try:
        for item in sorted(p.iterdir()):
            if item.name.startswith("."):
                continue
            files.append({
                "name": item.name,
                "path": str(item),
                "is_dir": item.is_dir(),
                "size": item.stat().st_size if item.is_file() else 0,
                "modified": item.stat().st_mtime,
            })
    except PermissionError:
        return {"files": [], "error": "Permission denied"}

    return {"files": files[:200], "path": str(p)}


def _files_organize(payload: dict) -> dict:
    engine = _get("engine")
    if not engine:
        return {"error": "Organization engine not available"}

    path = payload.get("path", "")
    dry_run = payload.get("dryRun", False)
    try:
        result = engine.organize(path, dry_run=dry_run)
        return {"success": True, "result": result}
    except Exception as e:
        return {"error": str(e)}


def _files_undo(payload: dict) -> dict:
    try:
        from sortmeout.core.history import ActionHistory
        history = ActionHistory()
        result = history.undo_last()
        return {"success": True, "result": str(result)}
    except Exception as e:
        return {"error": str(e)}


def _files_search(payload: dict) -> dict:
    query = payload.get("query", "")
    path = payload.get("path", str(Path.home()))
    try:
        from sortmeout.macos.spotlight import SpotlightSearch
        spotlight = SpotlightSearch()
        results = spotlight.search(query, path)
        return {"files": results if isinstance(results, list) else []}
    except Exception as e:
        return {"files": [], "error": str(e)}


def _files_info(payload: dict) -> dict:
    path = payload.get("path", "")
    p = Path(path)
    if not p.exists():
        return {"error": "File not found"}
    try:
        from sortmeout.utils.file_info import get_file_info
        info = get_file_info(str(p))
        return info if isinstance(info, dict) else {"path": str(p)}
    except Exception as e:
        return {"path": str(p), "error": str(e)}


def _files_move(payload: dict) -> dict:
    import shutil
    src = payload.get("src", "")
    dst = payload.get("dst", "")
    try:
        shutil.move(src, dst)
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


def _files_trash(payload: dict) -> dict:
    path = payload.get("path", "")
    try:
        from sortmeout.macos.trash import move_to_trash
        move_to_trash(path)
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


def _files_tag(payload: dict) -> dict:
    path = payload.get("path", "")
    tags = payload.get("tags", [])
    try:
        from sortmeout.macos.tags import set_tags
        set_tags(path, tags)
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# SETTINGS
# ─────────────────────────────────────────────────────────────────────────────

def _settings_get(payload: dict) -> dict:
    try:
        from sortmeout.config import manager as cfg_manager
        config = cfg_manager.load_config()
        return {
            "darkMode": config.get("dark_mode", True),
            "autoLaunch": config.get("auto_launch", False),
            "notifications": config.get("notifications", True),
            "model": config.get("model", "claude-sonnet-4-20250514"),
            "watchFolders": config.get("watch_folders", []),
        }
    except Exception:
        return {
            "darkMode": True,
            "autoLaunch": False,
            "notifications": True,
            "model": "claude-sonnet-4-20250514",
        }


def _settings_update(payload: dict) -> dict:
    try:
        from sortmeout.config import manager as cfg_manager
        config = cfg_manager.load_config()
        for key, value in payload.items():
            # Map JS camelCase → Python snake_case
            py_key = "".join(
                f"_{c.lower()}" if c.isupper() else c for c in key
            ).lstrip("_")
            config[py_key] = value
        cfg_manager.save_config(config)
        return {"success": True}
    except Exception as e:
        return {"error": str(e)}


def _settings_watch_folders(payload: dict) -> dict:
    try:
        from sortmeout.config import manager as cfg_manager
        config = cfg_manager.load_config()
        return {"folders": config.get("watch_folders", [])}
    except Exception:
        return {"folders": []}


# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM
# ─────────────────────────────────────────────────────────────────────────────

def _system_status(payload: dict) -> dict:
    return {
        "ai": True,
        "watcher": True,
        "scheduler": True,
        "monitor": True,
        "version": "1.0.1",
    }


def _system_open_folder(payload: dict) -> dict:
    path = payload.get("path", "")
    subprocess.Popen(["open", path])
    return {"success": True}


def _system_open_file(payload: dict) -> dict:
    path = payload.get("path", "")
    subprocess.Popen(["open", path])
    return {"success": True}


def _system_clipboard(payload: dict) -> dict:
    text = payload.get("text", "")
    process = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
    process.communicate(text.encode("utf-8"))
    return {"success": True}


# ═══════════════════════════════════════════════════════════════════════════════
# HANDLER REGISTRY
# ═══════════════════════════════════════════════════════════════════════════════

_HANDLERS: dict[str, Any] = {
    # Chat
    "chat_send": _chat_send,
    "chat_clear": _chat_clear,
    "chat_history": _chat_history,

    # Email
    "email_list": _email_list,
    "email_compose": _email_compose,
    "email_reply": _email_reply,
    "email_search": _email_search,
    "email_search_all": _email_search_all,
    "email_unread": _email_unread,

    # Messages
    "msg_send": _msg_send,
    "msg_read": _msg_read,

    # Calendar
    "cal_events": _cal_events,
    "cal_create": _cal_create,
    "cal_edit": _cal_edit,
    "cal_delete": _cal_delete,

    # Contacts
    "contacts_search": _contacts_search,
    "contacts_create": _contacts_create,
    "contacts_edit": _contacts_edit,
    "contacts_delete": _contacts_delete,

    # Notes
    "notes_list": _notes_list,
    "notes_create": _notes_create,
    "notes_search": _notes_search,
    "notes_edit": _notes_edit,
    "notes_delete": _notes_delete,

    # Presentations
    "pres_create": _pres_create,
    "pres_add_slide": _pres_add_slide,

    # Images
    "img_generate": _img_generate,
    "img_edit": _img_edit,
    "img_gallery": _img_gallery,

    # Rules
    "rules_list": _rules_list,
    "rules_create": _rules_create,
    "rules_delete": _rules_delete,
    "rules_toggle": _rules_toggle,

    # Files
    "files_list": _files_list,
    "files_organize": _files_organize,
    "files_undo": _files_undo,
    "files_search": _files_search,
    "files_info": _files_info,
    "files_move": _files_move,
    "files_trash": _files_trash,
    "files_tag": _files_tag,

    # Settings
    "settings_get": _settings_get,
    "settings_update": _settings_update,
    "settings_watch_folders": _settings_watch_folders,

    # System
    "system_status": _system_status,
    "system_open_folder": _system_open_folder,
    "system_open_file": _system_open_file,
    "system_clipboard": _system_clipboard,
}
