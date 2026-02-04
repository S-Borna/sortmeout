"""
Condition definitions for rule matching.

Conditions define the criteria that files must meet to match a rule.
They can be combined using groups with AND, OR, NOT logic.
"""

from __future__ import annotations

import fnmatch
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union
import uuid


class ConditionAttribute(Enum):
    """Available attributes for conditions."""
    # File name attributes
    NAME = "name"
    EXTENSION = "extension"
    FULL_NAME = "full_name"  # name + extension

    # Path attributes
    PATH = "path"
    PARENT_FOLDER = "parent_folder"

    # Size attributes
    SIZE = "size"
    SIZE_BYTES = "size_bytes"

    # Date attributes
    DATE_CREATED = "date_created"
    DATE_MODIFIED = "date_modified"
    DATE_ACCESSED = "date_accessed"
    DATE_ADDED = "date_added"  # macOS specific

    # Type attributes
    FILE_TYPE = "file_type"  # MIME type
    KIND = "kind"  # macOS kind (e.g., "PDF document")
    UTI = "uti"  # Uniform Type Identifier

    # Content attributes
    CONTENTS = "contents"  # Text file contents

    # macOS specific
    TAGS = "tags"
    FINDER_COMMENT = "finder_comment"
    WHERE_FROM = "where_from"  # Download source URL
    SPOTLIGHT = "spotlight"  # Any Spotlight attribute

    # Custom
    CUSTOM = "custom"


class ConditionOperator(Enum):
    """Available operators for conditions."""
    # String operators
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    MATCHES_REGEX = "matches_regex"
    MATCHES_GLOB = "matches_glob"

    # Numeric operators
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_OR_EQUAL = "greater_or_equal"
    LESS_OR_EQUAL = "less_or_equal"
    BETWEEN = "between"

    # Date operators
    IS_TODAY = "is_today"
    IS_YESTERDAY = "is_yesterday"
    IS_THIS_WEEK = "is_this_week"
    IS_LAST_WEEK = "is_last_week"
    IS_THIS_MONTH = "is_this_month"
    IS_LAST_MONTH = "is_last_month"
    IS_THIS_YEAR = "is_this_year"
    WITHIN_LAST = "within_last"  # e.g., within last 7 days
    NOT_WITHIN_LAST = "not_within_last"
    BEFORE = "before"
    AFTER = "after"

    # List operators
    IN_LIST = "in_list"
    NOT_IN_LIST = "not_in_list"

    # Boolean operators
    IS_TRUE = "is_true"
    IS_FALSE = "is_false"

    # Existence operators
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"
    IS_EMPTY = "is_empty"
    IS_NOT_EMPTY = "is_not_empty"


class ConditionGroupMode(Enum):
    """How conditions in a group are combined."""
    ALL = "all"  # AND
    ANY = "any"  # OR
    NONE = "none"  # NOT


def parse_size(size_str: str) -> int:
    """
    Parse a size string into bytes.

    Args:
        size_str: Size string like "10MB", "1.5GB", "500KB"

    Returns:
        Size in bytes.
    """
    if isinstance(size_str, (int, float)):
        return int(size_str)

    size_str = size_str.strip().upper()

    units = {
        'B': 1,
        'KB': 1024,
        'MB': 1024 ** 2,
        'GB': 1024 ** 3,
        'TB': 1024 ** 4,
        'K': 1024,
        'M': 1024 ** 2,
        'G': 1024 ** 3,
        'T': 1024 ** 4,
    }

    # Match number followed by optional unit
    match = re.match(r'^([\d.]+)\s*([A-Z]*B?)$', size_str)
    if match:
        number = float(match.group(1))
        unit = match.group(2) or 'B'
        return int(number * units.get(unit, 1))

    return int(float(size_str))


def parse_duration(duration_str: str) -> timedelta:
    """
    Parse a duration string into timedelta.

    Args:
        duration_str: Duration string like "7 days", "2 hours", "30 minutes"

    Returns:
        timedelta object.
    """
    if isinstance(duration_str, timedelta):
        return duration_str

    duration_str = duration_str.strip().lower()

    patterns = [
        (r'(\d+)\s*(?:d|days?)', lambda m: timedelta(days=int(m.group(1)))),
        (r'(\d+)\s*(?:h|hours?)', lambda m: timedelta(hours=int(m.group(1)))),
        (r'(\d+)\s*(?:m|min(?:utes?)?)', lambda m: timedelta(minutes=int(m.group(1)))),
        (r'(\d+)\s*(?:s|sec(?:onds?)?)', lambda m: timedelta(seconds=int(m.group(1)))),
        (r'(\d+)\s*(?:w|weeks?)', lambda m: timedelta(weeks=int(m.group(1)))),
    ]

    for pattern, handler in patterns:
        match = re.match(pattern, duration_str)
        if match:
            return handler(match)

    # Default to days if no unit specified
    return timedelta(days=int(duration_str))


@dataclass
class Condition:
    """
    A single condition for file matching.

    Attributes:
        attribute: The file attribute to check.
        operator: The comparison operator.
        value: The value to compare against.
        case_sensitive: Whether string comparisons are case-sensitive.
        negate: Invert the condition result.
        id: Unique identifier.

    Example:
        >>> cond = Condition("extension", "equals", "pdf")
        >>> cond.evaluate({"extension": "pdf"})
        True
    """

    attribute: str | ConditionAttribute
    operator: str | ConditionOperator
    value: Any
    case_sensitive: bool = False
    negate: bool = False
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self) -> None:
        """Normalize attribute and operator to enum values."""
        if isinstance(self.attribute, str):
            try:
                self.attribute = ConditionAttribute(self.attribute)
            except ValueError:
                # Keep as string for custom attributes
                pass

        if isinstance(self.operator, str):
            self.operator = ConditionOperator(self.operator)

    def evaluate(self, file_info: Dict[str, Any]) -> bool:
        """
        Evaluate the condition against file information.

        Args:
            file_info: Dictionary containing file attributes.

        Returns:
            True if the condition is satisfied.
        """
        # Get the attribute value from file_info
        attr_name = self.attribute.value if isinstance(self.attribute, ConditionAttribute) else self.attribute
        actual_value = file_info.get(attr_name)

        # Handle missing attributes
        if actual_value is None:
            if self.operator in (ConditionOperator.NOT_EXISTS, ConditionOperator.IS_EMPTY):
                result = True
            elif self.operator in (ConditionOperator.EXISTS, ConditionOperator.IS_NOT_EMPTY):
                result = False
            else:
                result = False
        else:
            result = self._compare(actual_value, self.value, self.operator)

        return not result if self.negate else result

    def _compare(self, actual: Any, expected: Any, operator: ConditionOperator) -> bool:
        """
        Perform the comparison.

        Args:
            actual: The actual value from the file.
            expected: The expected value from the condition.
            operator: The comparison operator.

        Returns:
            True if the comparison succeeds.
        """
        # String operations
        if operator == ConditionOperator.EQUALS:
            return self._str_compare(actual, expected, lambda a, b: a == b)

        elif operator == ConditionOperator.NOT_EQUALS:
            return self._str_compare(actual, expected, lambda a, b: a != b)

        elif operator == ConditionOperator.CONTAINS:
            return self._str_compare(actual, expected, lambda a, b: b in a)

        elif operator == ConditionOperator.NOT_CONTAINS:
            return self._str_compare(actual, expected, lambda a, b: b not in a)

        elif operator == ConditionOperator.STARTS_WITH:
            return self._str_compare(actual, expected, lambda a, b: a.startswith(b))

        elif operator == ConditionOperator.ENDS_WITH:
            return self._str_compare(actual, expected, lambda a, b: a.endswith(b))

        elif operator == ConditionOperator.MATCHES_REGEX:
            flags = 0 if self.case_sensitive else re.IGNORECASE
            try:
                return bool(re.search(expected, str(actual), flags))
            except re.error:
                return False

        elif operator == ConditionOperator.MATCHES_GLOB:
            actual_str = str(actual)
            if not self.case_sensitive:
                actual_str = actual_str.lower()
                expected = expected.lower()
            return fnmatch.fnmatch(actual_str, expected)

        # Numeric operations
        elif operator == ConditionOperator.GREATER_THAN:
            return self._num_compare(actual, expected, lambda a, b: a > b)

        elif operator == ConditionOperator.LESS_THAN:
            return self._num_compare(actual, expected, lambda a, b: a < b)

        elif operator == ConditionOperator.GREATER_OR_EQUAL:
            return self._num_compare(actual, expected, lambda a, b: a >= b)

        elif operator == ConditionOperator.LESS_OR_EQUAL:
            return self._num_compare(actual, expected, lambda a, b: a <= b)

        elif operator == ConditionOperator.BETWEEN:
            if isinstance(expected, (list, tuple)) and len(expected) == 2:
                low, high = expected
                return self._num_compare(actual, low, lambda a, b: a >= b) and \
                       self._num_compare(actual, high, lambda a, b: a <= b)
            return False

        # Date operations
        elif operator == ConditionOperator.IS_TODAY:
            return self._is_same_day(actual, datetime.now())

        elif operator == ConditionOperator.IS_YESTERDAY:
            return self._is_same_day(actual, datetime.now() - timedelta(days=1))

        elif operator == ConditionOperator.IS_THIS_WEEK:
            return self._is_this_week(actual)

        elif operator == ConditionOperator.IS_LAST_WEEK:
            return self._is_last_week(actual)

        elif operator == ConditionOperator.IS_THIS_MONTH:
            return self._is_this_month(actual)

        elif operator == ConditionOperator.IS_LAST_MONTH:
            return self._is_last_month(actual)

        elif operator == ConditionOperator.IS_THIS_YEAR:
            return self._is_this_year(actual)

        elif operator == ConditionOperator.WITHIN_LAST:
            delta = parse_duration(expected) if isinstance(expected, str) else expected
            if isinstance(actual, datetime):
                return actual >= datetime.now() - delta
            return False

        elif operator == ConditionOperator.NOT_WITHIN_LAST:
            delta = parse_duration(expected) if isinstance(expected, str) else expected
            if isinstance(actual, datetime):
                return actual < datetime.now() - delta
            return False

        elif operator == ConditionOperator.BEFORE:
            if isinstance(actual, datetime) and isinstance(expected, datetime):
                return actual < expected
            return False

        elif operator == ConditionOperator.AFTER:
            if isinstance(actual, datetime) and isinstance(expected, datetime):
                return actual > expected
            return False

        # List operations
        elif operator == ConditionOperator.IN_LIST:
            if isinstance(expected, (list, tuple)):
                if not self.case_sensitive and isinstance(actual, str):
                    return actual.lower() in [str(e).lower() for e in expected]
                return actual in expected
            return False

        elif operator == ConditionOperator.NOT_IN_LIST:
            if isinstance(expected, (list, tuple)):
                if not self.case_sensitive and isinstance(actual, str):
                    return actual.lower() not in [str(e).lower() for e in expected]
                return actual not in expected
            return True

        # Boolean operations
        elif operator == ConditionOperator.IS_TRUE:
            return bool(actual)

        elif operator == ConditionOperator.IS_FALSE:
            return not bool(actual)

        # Existence operations
        elif operator == ConditionOperator.EXISTS:
            return actual is not None

        elif operator == ConditionOperator.NOT_EXISTS:
            return actual is None

        elif operator == ConditionOperator.IS_EMPTY:
            if actual is None:
                return True
            if isinstance(actual, str):
                return len(actual.strip()) == 0
            if hasattr(actual, '__len__'):
                return len(actual) == 0
            return False

        elif operator == ConditionOperator.IS_NOT_EMPTY:
            if actual is None:
                return False
            if isinstance(actual, str):
                return len(actual.strip()) > 0
            if hasattr(actual, '__len__'):
                return len(actual) > 0
            return True

        return False

    def _str_compare(self, actual: Any, expected: Any, comparator: Callable[[str, str], bool]) -> bool:
        """String comparison with case sensitivity handling."""
        actual_str = str(actual)
        expected_str = str(expected)

        if not self.case_sensitive:
            actual_str = actual_str.lower()
            expected_str = expected_str.lower()

        return comparator(actual_str, expected_str)

    def _num_compare(self, actual: Any, expected: Any, comparator: Callable[[float, float], bool]) -> bool:
        """Numeric comparison with size string parsing."""
        try:
            # Handle size strings
            if isinstance(expected, str) and any(c.isalpha() for c in expected):
                expected = parse_size(expected)
            if isinstance(actual, str) and any(c.isalpha() for c in actual):
                actual = parse_size(actual)

            return comparator(float(actual), float(expected))
        except (ValueError, TypeError):
            return False

    def _is_same_day(self, date: Any, target: datetime) -> bool:
        """Check if date is the same day as target."""
        if isinstance(date, datetime):
            return date.date() == target.date()
        return False

    def _is_this_week(self, date: Any) -> bool:
        """Check if date is in the current week."""
        if isinstance(date, datetime):
            now = datetime.now()
            start_of_week = now - timedelta(days=now.weekday())
            start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_week = start_of_week + timedelta(days=7)
            return start_of_week <= date < end_of_week
        return False

    def _is_last_week(self, date: Any) -> bool:
        """Check if date is in the previous week."""
        if isinstance(date, datetime):
            now = datetime.now()
            start_of_this_week = now - timedelta(days=now.weekday())
            start_of_this_week = start_of_this_week.replace(hour=0, minute=0, second=0, microsecond=0)
            start_of_last_week = start_of_this_week - timedelta(days=7)
            return start_of_last_week <= date < start_of_this_week
        return False

    def _is_this_month(self, date: Any) -> bool:
        """Check if date is in the current month."""
        if isinstance(date, datetime):
            now = datetime.now()
            return date.year == now.year and date.month == now.month
        return False

    def _is_last_month(self, date: Any) -> bool:
        """Check if date is in the previous month."""
        if isinstance(date, datetime):
            now = datetime.now()
            last_month = now.replace(day=1) - timedelta(days=1)
            return date.year == last_month.year and date.month == last_month.month
        return False

    def _is_this_year(self, date: Any) -> bool:
        """Check if date is in the current year."""
        if isinstance(date, datetime):
            return date.year == datetime.now().year
        return False

    def duplicate(self) -> "Condition":
        """Create a copy of this condition."""
        return Condition(
            attribute=self.attribute,
            operator=self.operator,
            value=self.value,
            case_sensitive=self.case_sensitive,
            negate=self.negate,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert condition to dictionary for serialization."""
        attr = self.attribute.value if isinstance(self.attribute, ConditionAttribute) else self.attribute
        op = self.operator.value if isinstance(self.operator, ConditionOperator) else self.operator

        return {
            "id": self.id,
            "attribute": attr,
            "operator": op,
            "value": self.value,
            "case_sensitive": self.case_sensitive,
            "negate": self.negate,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Condition":
        """Create a condition from a dictionary."""
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            attribute=data["attribute"],
            operator=data["operator"],
            value=data["value"],
            case_sensitive=data.get("case_sensitive", False),
            negate=data.get("negate", False),
        )

    def __str__(self) -> str:
        """Human-readable representation."""
        attr = self.attribute.value if isinstance(self.attribute, ConditionAttribute) else self.attribute
        op = self.operator.value if isinstance(self.operator, ConditionOperator) else self.operator
        neg = "NOT " if self.negate else ""
        return f"{neg}{attr} {op} {self.value!r}"


@dataclass
class ConditionGroup:
    """
    A group of conditions combined with AND, OR, or NOT logic.

    Condition groups allow for complex nested logic in rules.

    Attributes:
        conditions: List of conditions or nested groups.
        mode: How conditions are combined (all, any, none).
        id: Unique identifier.

    Example:
        >>> group = ConditionGroup(
        ...     conditions=[
        ...         Condition("extension", "equals", "pdf"),
        ...         Condition("size", "greater_than", "1MB"),
        ...     ],
        ...     mode=ConditionGroupMode.ALL
        ... )
    """

    conditions: List[Condition | "ConditionGroup"]
    mode: ConditionGroupMode = ConditionGroupMode.ALL
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self) -> None:
        """Normalize mode to enum."""
        if isinstance(self.mode, str):
            self.mode = ConditionGroupMode(self.mode)

    def evaluate(self, file_info: Dict[str, Any]) -> bool:
        """
        Evaluate the condition group against file information.

        Args:
            file_info: Dictionary containing file attributes.

        Returns:
            True if the condition group is satisfied.
        """
        if not self.conditions:
            return True

        results = [cond.evaluate(file_info) for cond in self.conditions]

        if self.mode == ConditionGroupMode.ALL:
            return all(results)
        elif self.mode == ConditionGroupMode.ANY:
            return any(results)
        elif self.mode == ConditionGroupMode.NONE:
            return not any(results)

        return False

    def add_condition(self, condition: Condition | "ConditionGroup") -> "ConditionGroup":
        """Add a condition to the group."""
        self.conditions.append(condition)
        return self

    def duplicate(self) -> "ConditionGroup":
        """Create a copy of this condition group."""
        return ConditionGroup(
            conditions=[c.duplicate() for c in self.conditions],
            mode=self.mode,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert condition group to dictionary for serialization."""
        return {
            "id": self.id,
            "mode": self.mode.value,
            "conditions": [c.to_dict() for c in self.conditions],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConditionGroup":
        """Create a condition group from a dictionary."""
        conditions = []
        for cond_data in data.get("conditions", []):
            if "conditions" in cond_data:
                conditions.append(cls.from_dict(cond_data))
            else:
                conditions.append(Condition.from_dict(cond_data))

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            mode=ConditionGroupMode(data.get("mode", "all")),
            conditions=conditions,
        )

    def __str__(self) -> str:
        """Human-readable representation."""
        mode_str = self.mode.value.upper()
        conditions_str = f" {mode_str} ".join(str(c) for c in self.conditions)
        return f"({conditions_str})"


# Convenience functions for creating common conditions

def name_equals(value: str, case_sensitive: bool = False) -> Condition:
    """Create a condition that checks if file name equals value."""
    return Condition("name", "equals", value, case_sensitive=case_sensitive)


def name_contains(value: str, case_sensitive: bool = False) -> Condition:
    """Create a condition that checks if file name contains value."""
    return Condition("name", "contains", value, case_sensitive=case_sensitive)


def extension_is(ext: str) -> Condition:
    """Create a condition that checks file extension."""
    # Remove leading dot if present
    ext = ext.lstrip(".")
    return Condition("extension", "equals", ext, case_sensitive=False)


def extension_in(extensions: List[str]) -> Condition:
    """Create a condition that checks if extension is in list."""
    # Remove leading dots
    extensions = [e.lstrip(".") for e in extensions]
    return Condition("extension", "in_list", extensions, case_sensitive=False)


def size_greater_than(size: str | int) -> Condition:
    """Create a condition that checks if file size is greater than value."""
    return Condition("size", "greater_than", size)


def size_less_than(size: str | int) -> Condition:
    """Create a condition that checks if file size is less than value."""
    return Condition("size", "less_than", size)


def modified_within(duration: str) -> Condition:
    """Create a condition that checks if file was modified within duration."""
    return Condition("date_modified", "within_last", duration)


def created_within(duration: str) -> Condition:
    """Create a condition that checks if file was created within duration."""
    return Condition("date_created", "within_last", duration)


def has_tag(tag: str) -> Condition:
    """Create a condition that checks if file has a specific tag."""
    return Condition("tags", "contains", tag)


def from_url(url_pattern: str) -> Condition:
    """Create a condition that checks download source URL."""
    return Condition("where_from", "contains", url_pattern)
