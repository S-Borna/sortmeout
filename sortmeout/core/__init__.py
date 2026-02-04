"""
Core module for SortMeOut.

Contains the fundamental building blocks of the file automation system.
"""

from sortmeout.core.rule import Rule
from sortmeout.core.condition import Condition, ConditionGroup
from sortmeout.core.action import Action
from sortmeout.core.watcher import FolderWatcher, WatcherManager
from sortmeout.core.engine import RuleEngine

__all__ = [
    "Rule",
    "Condition",
    "ConditionGroup",
    "Action",
    "FolderWatcher",
    "WatcherManager",
    "RuleEngine",
]
