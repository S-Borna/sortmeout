"""
Core module for SortMeOut.

Contains the fundamental building blocks of the file automation system.
"""

from sortmeout.core.rule import Rule
from sortmeout.core.condition import Condition, ConditionGroup
from sortmeout.core.action import Action
from sortmeout.core.watcher import FolderWatcher, WatcherManager
from sortmeout.core.engine import RuleEngine
from sortmeout.core.history import HistoryManager, get_history, record_action
from sortmeout.core.scheduler import Scheduler, ScheduledRule, ScheduleInterval
from sortmeout.core.templates import get_templates, get_onboarding_templates

__all__ = [
    "Rule",
    "Condition",
    "ConditionGroup",
    "Action",
    "FolderWatcher",
    "WatcherManager",
    "RuleEngine",
    "HistoryManager",
    "get_history",
    "record_action",
    "Scheduler",
    "ScheduledRule",
    "ScheduleInterval",
    "get_templates",
    "get_onboarding_templates",
]
