"""
SortMeOut - Intelligent file automation for macOS.

A powerful, rule-based file organization system with AI-powered assistance.
"""

__version__ = "1.0.1"
__author__ = "Said Borna"
__license__ = "Proprietary"

from sortmeout.app import SortMeOut
from sortmeout.core.rule import Rule
from sortmeout.core.condition import Condition, ConditionGroup
from sortmeout.core.action import Action

__all__ = [
    "SortMeOut",
    "Rule",
    "Condition",
    "ConditionGroup",
    "Action",
    "__version__",
]
