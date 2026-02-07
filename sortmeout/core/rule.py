"""
Rule definition and management.

Rules are the core concept in SortMeOut. Each rule consists of:
- Conditions: Criteria that a file must match
- Actions: Operations to perform on matching files
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from sortmeout.core.condition import Condition, ConditionGroup
from sortmeout.core.action import Action


class RuleMatchMode(Enum):
    """How conditions are combined when matching."""
    ALL = "all"  # All conditions must match (AND)
    ANY = "any"  # Any condition must match (OR)
    NONE = "none"  # No conditions must match (NOT)


@dataclass
class Rule:
    """
    A rule that defines conditions and actions for file processing.

    Rules are evaluated in order. When a file matches a rule's conditions,
    the rule's actions are executed. By default, processing stops after
    the first matching rule, but this can be changed with continue_processing.

    Attributes:
        name: Human-readable name for the rule.
        conditions: List of conditions that must be satisfied.
        actions: List of actions to perform on matching files.
        enabled: Whether the rule is active.
        match_mode: How conditions are combined (all, any, none).
        continue_processing: Continue with next rules after match.
        run_on_folder_open: Run rule when folder is first opened.
        id: Unique identifier for the rule.
        created_at: When the rule was created.
        updated_at: When the rule was last updated.
        description: Optional description of the rule.

    Example:
        >>> rule = Rule(
        ...     name="Organize PDFs",
        ...     conditions=[
        ...         Condition("extension", "equals", "pdf"),
        ...         Condition("size", "greater_than", "1MB"),
        ...     ],
        ...     actions=[
        ...         Action("move", destination="~/Documents/PDFs"),
        ...     ]
        ... )
    """

    name: str
    conditions: List[Condition | ConditionGroup] = field(default_factory=list)
    actions: List[Action] = field(default_factory=list)
    enabled: bool = True
    match_mode: RuleMatchMode = RuleMatchMode.ALL
    continue_processing: bool = False
    run_on_folder_open: bool = True
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    description: Optional[str] = None
    priority: int = 0
    run_count: int = 0
    last_run: Optional[datetime] = None

    def __post_init__(self) -> None:
        """Normalize rule after initialization."""
        if isinstance(self.match_mode, str):
            self.match_mode = RuleMatchMode(self.match_mode)

    def matches(self, file_info: Dict[str, Any]) -> bool:
        """
        Check if a file matches this rule's conditions.

        Args:
            file_info: Dictionary containing file attributes.

        Returns:
            True if the file matches the rule's conditions.
        """
        if not self.enabled:
            return False

        if not self.conditions:
            # No conditions means always match
            return True

        results = [cond.evaluate(file_info) for cond in self.conditions]

        if self.match_mode == RuleMatchMode.ALL:
            return all(results)
        elif self.match_mode == RuleMatchMode.ANY:
            return any(results)
        elif self.match_mode == RuleMatchMode.NONE:
            return not any(results)

        return False

    def add_condition(self, condition: Condition | ConditionGroup) -> "Rule":
        """
        Add a condition to the rule.

        Args:
            condition: Condition to add.

        Returns:
            Self for chaining.
        """
        self.conditions.append(condition)
        self.updated_at = datetime.now()
        return self

    def add_action(self, action: Action) -> "Rule":
        """
        Add an action to the rule.

        Args:
            action: Action to add.

        Returns:
            Self for chaining.
        """
        self.actions.append(action)
        self.updated_at = datetime.now()
        return self

    def remove_condition(self, condition_id) -> bool:
        """
        Remove a condition by ID or index.

        Args:
            condition_id: ID string or integer index of condition to remove.

        Returns:
            True if condition was removed.
        """
        if isinstance(condition_id, int):
            if 0 <= condition_id < len(self.conditions):
                del self.conditions[condition_id]
                self.updated_at = datetime.now()
                return True
            return False
        for i, c in enumerate(self.conditions):
            if hasattr(c, 'id') and c.id == condition_id:
                del self.conditions[i]
                self.updated_at = datetime.now()
                return True
        return False

    def remove_action(self, action_id) -> bool:
        """
        Remove an action by ID or index.

        Args:
            action_id: ID string or integer index of action to remove.

        Returns:
            True if action was removed.
        """
        if isinstance(action_id, int):
            if 0 <= action_id < len(self.actions):
                del self.actions[action_id]
                self.updated_at = datetime.now()
                return True
            return False
        for i, a in enumerate(self.actions):
            if hasattr(a, 'id') and a.id == action_id:
                del self.actions[i]
                self.updated_at = datetime.now()
                return True
        return False

    def clear_conditions(self) -> None:
        """Remove all conditions."""
        self.conditions.clear()
        self.updated_at = datetime.now()

    def clear_actions(self) -> None:
        """Remove all actions."""
        self.actions.clear()
        self.updated_at = datetime.now()

    def record_run(self) -> None:
        """Record that this rule was executed."""
        self.run_count += 1
        self.last_run = datetime.now()

    def describe(self) -> str:
        """Generate a human-readable description of the rule."""
        if not self.conditions and not self.actions:
            return f"{self.name}: No conditions, no actions"

        parts = []
        if self.conditions:
            cond_strs = [str(c) for c in self.conditions]
            mode = self.match_mode.value.upper()
            parts.append(f"If {mode} of: {', '.join(cond_strs)}")
        else:
            parts.append("No conditions (matches all files)")

        if self.actions:
            action_strs = [
                a.action_type.value if hasattr(a.action_type, 'value') else str(a.action_type)
                for a in self.actions
            ]
            parts.append(f"Then: {', '.join(action_strs)}")
        else:
            parts.append("No actions")

        return f"{self.name}: {' → '.join(parts)}"

    def validate(self) -> List[str]:
        """
        Validate the rule configuration.

        Returns:
            List of validation error messages. Empty if valid.
        """
        errors = []
        if not self.name:
            errors.append("Rule name cannot be empty")
        if not self.actions:
            errors.append("Rule must have at least one action")
        return errors

    def duplicate(self, new_name: Optional[str] = None) -> "Rule":
        """
        Create a copy of this rule.

        Args:
            new_name: Name for the new rule.

        Returns:
            A new Rule instance.
        """
        return Rule(
            name=new_name or f"{self.name} (Copy)",
            conditions=[c.duplicate() for c in self.conditions],
            actions=[a.duplicate() for a in self.actions],
            enabled=self.enabled,
            match_mode=self.match_mode,
            continue_processing=self.continue_processing,
            run_on_folder_open=self.run_on_folder_open,
            description=self.description,
            priority=self.priority,
        )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert rule to dictionary for serialization.

        Returns:
            Dictionary representation of the rule.
        """
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "priority": self.priority,
            "match_mode": self.match_mode.value,
            "continue_processing": self.continue_processing,
            "run_on_folder_open": self.run_on_folder_open,
            "conditions": [c.to_dict() for c in self.conditions],
            "actions": [a.to_dict() for a in self.actions],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Rule":
        """
        Create a rule from a dictionary.

        Args:
            data: Dictionary containing rule data.

        Returns:
            A new Rule instance.
        """
        conditions = []
        for cond_data in data.get("conditions", []):
            if "conditions" in cond_data:  # It's a condition group
                conditions.append(ConditionGroup.from_dict(cond_data))
            else:
                conditions.append(Condition.from_dict(cond_data))

        actions = [Action.from_dict(a) for a in data.get("actions", [])]

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data["name"],
            description=data.get("description"),
            enabled=data.get("enabled", True),
            priority=data.get("priority", 0),
            match_mode=RuleMatchMode(data.get("match_mode", "all")),
            continue_processing=data.get("continue_processing", False),
            run_on_folder_open=data.get("run_on_folder_open", True),
            conditions=conditions,
            actions=actions,
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.now(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else datetime.now(),
        )

    def __str__(self) -> str:
        """String representation of the rule."""
        status = "✓" if self.enabled else "✗"
        return f"[{status}] {self.name} ({len(self.conditions)} conditions, {len(self.actions)} actions)"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return f"Rule(name={self.name!r}, enabled={self.enabled}, conditions={len(self.conditions)}, actions={len(self.actions)})"
