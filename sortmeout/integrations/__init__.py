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
"""

from sortmeout.integrations.mail import MailIntegration
from sortmeout.integrations.calendar import CalendarIntegration
from sortmeout.integrations.messages import MessagesIntegration
from sortmeout.integrations.contacts import ContactsIntegration
from sortmeout.integrations.presentations import PresentationBuilder
from sortmeout.integrations.notes import NotesIntegration
from sortmeout.integrations.monitor import ProactiveMonitor, get_monitor
from sortmeout.integrations.learner import BehaviorLearner, get_learner
from sortmeout.integrations.images import ImageEditor, ImageGenerator, get_editor, get_generator

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
