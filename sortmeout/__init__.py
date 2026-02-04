"""
SortMeOut - Open-source file automation and organization tool for macOS.

A powerful, rule-based file organization system inspired by Noodlesoft Hazel.
"""

__version__ = "1.0.0"
__author__ = "SortMeOut Contributors"
__license__ = "MIT"

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
