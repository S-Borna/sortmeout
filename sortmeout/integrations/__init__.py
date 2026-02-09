"""
SortMeOut Integrations — macOS system integrations for the ultimate AI assistant.

Modules:
    mail           — Read, compose, reply, search emails via Mail.app
    calendar       — Events, reminders, deadlines via Calendar.app
    messages       — Read and send iMessages
    contacts       — Access and search Contacts
    presentations  — Generate Keynote/PowerPoint presentations
    notes          — Read and create Apple Notes
    monitor        — Proactive background monitoring (mail/calendar alerts)
    learner        — Behavior learning engine (pattern detection & rule suggestions)
    images         — AI image generation (DALL-E 3) & editing (Pillow)

All imports are lazy to avoid loading heavy deps (ScriptingBridge,
Pillow, OpenAI) until actually needed.  Typical startup savings: ~250ms.
"""

_LAZY_IMPORTS = {
    "MailIntegration": "sortmeout.integrations.mail",
    "CalendarIntegration": "sortmeout.integrations.calendar",
    "MessagesIntegration": "sortmeout.integrations.messages",
    "ContactsIntegration": "sortmeout.integrations.contacts",
    "PresentationBuilder": "sortmeout.integrations.presentations",
    "NotesIntegration": "sortmeout.integrations.notes",
    "ProactiveMonitor": "sortmeout.integrations.monitor",
    "get_monitor": "sortmeout.integrations.monitor",
    "BehaviorLearner": "sortmeout.integrations.learner",
    "get_learner": "sortmeout.integrations.learner",
    "ImageEditor": "sortmeout.integrations.images",
    "ImageGenerator": "sortmeout.integrations.images",
    "get_editor": "sortmeout.integrations.images",
    "get_generator": "sortmeout.integrations.images",
}


def __getattr__(name):
    """Lazy import — only load a module when its symbol is first accessed."""
    if name in _LAZY_IMPORTS:
        import importlib

        module = importlib.import_module(_LAZY_IMPORTS[name])
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "MailIntegration",
    "CalendarIntegration",
    "MessagesIntegration",
    "ContactsIntegration",
    "PresentationBuilder",
    "NotesIntegration",
    "ProactiveMonitor",
    "get_monitor",
    "BehaviorLearner",
    "get_learner",
    "ImageEditor",
    "ImageGenerator",
    "get_editor",
    "get_generator",
]
