"""
Tests for the Rule class.
"""

import pytest
from datetime import datetime

from sortmeout.core.rule import Rule, RuleMatchMode as MatchMode
from sortmeout.core.condition import Condition, ConditionGroup
from sortmeout.core.action import Action, ActionType


class TestRuleCreation:
    """Tests for rule creation."""

    def test_create_rule_with_name(self):
        rule = Rule(name="My Rule")
        assert rule.name == "My Rule"
        assert rule.enabled is True

    def test_create_rule_with_defaults(self):
        rule = Rule(name="Test")
        assert rule.match_mode == MatchMode.ALL
        assert rule.enabled is True
        assert rule.conditions == []
        assert rule.actions == []
        assert rule.priority == 0

    def test_rule_has_unique_id(self):
        rule1 = Rule(name="Rule 1")
        rule2 = Rule(name="Rule 2")
        assert rule1.id != rule2.id


class TestMatchMode:
    """Tests for match modes."""

    def test_all_match_mode(self):
        rule = Rule(
            name="Test",
            match_mode=MatchMode.ALL,
            conditions=[
                Condition("name", "contains", "test"),
                Condition("extension", "equals", "txt"),
            ]
        )

        # Both match
        file_info = {"name": "test_file", "extension": "txt"}
        assert rule.matches(file_info)

        # Only one matches
        file_info = {"name": "test_file", "extension": "pdf"}
        assert not rule.matches(file_info)

    def test_any_match_mode(self):
        rule = Rule(
            name="Test",
            match_mode=MatchMode.ANY,
            conditions=[
                Condition("name", "contains", "test"),
                Condition("extension", "equals", "txt"),
            ]
        )

        # One matches
        file_info = {"name": "test_file", "extension": "pdf"}
        assert rule.matches(file_info)

        # Neither matches
        file_info = {"name": "file", "extension": "pdf"}
        assert not rule.matches(file_info)

    def test_none_match_mode(self):
        rule = Rule(
            name="Test",
            match_mode=MatchMode.NONE,
            conditions=[
                Condition("name", "contains", "test"),
                Condition("extension", "equals", "txt"),
            ]
        )

        # Neither matches
        file_info = {"name": "file", "extension": "pdf"}
        assert rule.matches(file_info)

        # One matches
        file_info = {"name": "test_file", "extension": "pdf"}
        assert not rule.matches(file_info)


class TestRuleConditions:
    """Tests for rule conditions management."""

    def test_add_condition(self):
        rule = Rule(name="Test")
        condition = Condition("name", "contains", "test")
        rule.add_condition(condition)

        assert len(rule.conditions) == 1
        assert rule.conditions[0] == condition

    def test_add_multiple_conditions(self):
        rule = Rule(name="Test")
        rule.add_condition(Condition("name", "contains", "test"))
        rule.add_condition(Condition("extension", "equals", "txt"))

        assert len(rule.conditions) == 2

    def test_remove_condition(self):
        condition = Condition("name", "contains", "test")
        rule = Rule(name="Test", conditions=[condition])

        rule.remove_condition(condition.id)

        assert len(rule.conditions) == 0

    def test_clear_conditions(self):
        rule = Rule(
            name="Test",
            conditions=[
                Condition("name", "contains", "test"),
                Condition("extension", "equals", "txt"),
            ]
        )

        rule.clear_conditions()

        assert len(rule.conditions) == 0


class TestRuleActions:
    """Tests for rule actions management."""

    def test_add_action(self):
        rule = Rule(name="Test")
        action = Action("move", destination="~/Documents")
        rule.add_action(action)

        assert len(rule.actions) == 1
        assert rule.actions[0] == action

    def test_add_multiple_actions(self):
        rule = Rule(name="Test")
        rule.add_action(Action("move", destination="~/Documents"))
        rule.add_action(Action("add_tags", tags=["processed"]))

        assert len(rule.actions) == 2

    def test_actions_preserve_order(self):
        rule = Rule(name="Test")
        action1 = Action("add_tags", tags=["step1"])
        action2 = Action("move", destination="~/Documents")
        action3 = Action("notify", message="Done")

        rule.add_action(action1)
        rule.add_action(action2)
        rule.add_action(action3)

        assert rule.actions[0] == action1
        assert rule.actions[1] == action2
        assert rule.actions[2] == action3

    def test_remove_action(self):
        action = Action("move", destination="~/Documents")
        rule = Rule(name="Test", actions=[action])

        rule.remove_action(action.id)

        assert len(rule.actions) == 0

    def test_clear_actions(self):
        rule = Rule(
            name="Test",
            actions=[
                Action("move", destination="~/Documents"),
                Action("notify", message="Done"),
            ]
        )

        rule.clear_actions()

        assert len(rule.actions) == 0


class TestRuleMatching:
    """Tests for rule matching."""

    def test_matches_file_info(self):
        rule = Rule(
            name="Text Files",
            conditions=[
                Condition("extension", "equals", "txt"),
            ]
        )

        assert rule.matches({"extension": "txt"})
        assert not rule.matches({"extension": "pdf"})

    def test_matches_with_condition_group(self):
        group = ConditionGroup(
            mode="any",
            conditions=[
                Condition("extension", "equals", "txt"),
                Condition("extension", "equals", "md"),
            ]
        )

        rule = Rule(
            name="Text Files",
            conditions=[group]
        )

        assert rule.matches({"extension": "txt"})
        assert rule.matches({"extension": "md"})
        assert not rule.matches({"extension": "pdf"})

    def test_disabled_rule_never_matches(self):
        rule = Rule(
            name="Test",
            enabled=False,
            conditions=[Condition("extension", "equals", "txt")]
        )

        assert not rule.matches({"extension": "txt"})

    def test_rule_without_conditions_matches_all(self):
        rule = Rule(name="Catch All")

        assert rule.matches({"extension": "txt"})
        assert rule.matches({"extension": "pdf"})
        assert rule.matches({})


class TestRulePriority:
    """Tests for rule priority."""

    def test_priority_sorting(self):
        rule1 = Rule(name="Low", priority=1)
        rule2 = Rule(name="High", priority=10)
        rule3 = Rule(name="Medium", priority=5)

        rules = [rule1, rule2, rule3]
        sorted_rules = sorted(rules, key=lambda r: r.priority, reverse=True)

        assert sorted_rules[0].name == "High"
        assert sorted_rules[1].name == "Medium"
        assert sorted_rules[2].name == "Low"


class TestRuleSerialization:
    """Tests for rule serialization."""

    def test_to_dict(self):
        rule = Rule(
            name="Test Rule",
            match_mode=MatchMode.ALL,
            conditions=[Condition("extension", "equals", "txt")],
            actions=[Action("move", destination="~/Documents")],
            priority=5,
            enabled=True,
        )

        data = rule.to_dict()

        assert data["name"] == "Test Rule"
        assert data["match_mode"] == "all"
        assert len(data["conditions"]) == 1
        assert len(data["actions"]) == 1
        assert data["priority"] == 5
        assert data["enabled"] is True

    def test_from_dict(self):
        data = {
            "name": "Test Rule",
            "match_mode": "any",
            "conditions": [
                {
                    "attribute": "extension",
                    "operator": "equals",
                    "value": "txt",
                }
            ],
            "actions": [
                {
                    "action_type": "move",
                    "params": {"destination": "~/Documents"},
                }
            ],
            "priority": 3,
            "enabled": False,
        }

        rule = Rule.from_dict(data)

        assert rule.name == "Test Rule"
        assert rule.match_mode == MatchMode.ANY
        assert len(rule.conditions) == 1
        assert len(rule.actions) == 1
        assert rule.priority == 3
        assert rule.enabled is False

    def test_duplicate(self):
        original = Rule(
            name="Original",
            conditions=[Condition("extension", "equals", "txt")],
            actions=[Action("move", destination="~/Documents")],
        )

        duplicate = original.duplicate()

        assert duplicate.name == "Original (Copy)"
        assert duplicate.id != original.id
        assert len(duplicate.conditions) == len(original.conditions)
        assert len(duplicate.actions) == len(original.actions)


class TestRuleStats:
    """Tests for rule statistics."""

    def test_initial_stats(self):
        rule = Rule(name="Test")

        assert rule.run_count == 0
        assert rule.last_run is None

    def test_record_run(self):
        rule = Rule(name="Test")

        rule.record_run()

        assert rule.run_count == 1
        assert rule.last_run is not None
        assert isinstance(rule.last_run, datetime)

    def test_multiple_runs(self):
        rule = Rule(name="Test")

        rule.record_run()
        first_run = rule.last_run

        rule.record_run()
        second_run = rule.last_run

        assert rule.run_count == 2
        assert second_run >= first_run


class TestRuleDescription:
    """Tests for rule description generation."""

    def test_simple_description(self):
        rule = Rule(
            name="Test",
            conditions=[Condition("extension", "equals", "txt")],
            actions=[Action("move", destination="~/Documents")],
        )

        desc = rule.describe()

        assert "extension" in desc.lower()
        assert "move" in desc.lower()

    def test_empty_rule_description(self):
        rule = Rule(name="Empty")

        desc = rule.describe()

        assert "no conditions" in desc.lower()


class TestRuleValidation:
    """Tests for rule validation."""

    def test_validate_complete_rule(self):
        rule = Rule(
            name="Valid Rule",
            conditions=[Condition("extension", "equals", "txt")],
            actions=[Action("move", destination="~/Documents")],
        )

        errors = rule.validate()

        assert len(errors) == 0

    def test_validate_missing_name(self):
        rule = Rule(name="")

        errors = rule.validate()

        assert any("name" in e.lower() for e in errors)

    def test_validate_no_actions(self):
        rule = Rule(
            name="No Actions",
            conditions=[Condition("extension", "equals", "txt")],
        )

        errors = rule.validate()

        assert any("action" in e.lower() for e in errors)
