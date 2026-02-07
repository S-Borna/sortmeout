"""Tests for the template rules system."""

import pytest

from sortmeout.core.templates import (
    get_templates,
    get_templates_by_category,
    get_categories,
    get_template_by_name,
    template_to_rule_dict,
    get_onboarding_templates,
)


class TestTemplates:
    """Tests for template functions."""

    def test_get_templates_not_empty(self):
        templates = get_templates()
        assert len(templates) > 0

    def test_templates_have_required_fields(self):
        for t in get_templates():
            assert "name" in t
            assert "description" in t
            assert "category" in t
            assert "conditions" in t
            assert "actions" in t

    def test_get_categories(self):
        categories = get_categories()
        assert len(categories) > 0
        assert "Downloads" in categories
        assert "Cleanup" in categories

    def test_get_templates_by_category(self):
        downloads = get_templates_by_category("Downloads")
        assert len(downloads) > 0
        assert all(t["category"] == "Downloads" for t in downloads)

    def test_get_templates_by_category_case_insensitive(self):
        result1 = get_templates_by_category("downloads")
        result2 = get_templates_by_category("Downloads")
        assert len(result1) == len(result2)

    def test_get_template_by_name(self):
        t = get_template_by_name("Organize Images")
        assert t is not None
        assert t["name"] == "Organize Images"
        assert len(t["conditions"]) > 0
        assert len(t["actions"]) > 0

    def test_get_template_by_name_not_found(self):
        t = get_template_by_name("Nonexistent Rule")
        assert t is None

    def test_get_template_by_name_case_insensitive(self):
        t = get_template_by_name("organize images")
        assert t is not None

    def test_template_to_rule_dict(self):
        t = get_template_by_name("Organize Images")
        rule_dict = template_to_rule_dict(t)
        assert rule_dict["name"] == "Organize Images"
        assert rule_dict["enabled"] is True
        assert "conditions" in rule_dict
        assert "actions" in rule_dict
        assert "folder" in rule_dict

    def test_template_to_rule_dict_custom_folder(self):
        t = get_template_by_name("Organize Images")
        rule_dict = template_to_rule_dict(t, folder="~/Desktop")
        assert rule_dict["folder"] == "~/Desktop"

    def test_onboarding_templates(self):
        templates = get_onboarding_templates()
        assert len(templates) > 0
        names = [t["name"] for t in templates]
        assert "Organize Images" in names
        assert "Organize Documents" in names

    def test_all_conditions_have_valid_operators(self):
        """Verify all template conditions use valid operators."""
        valid_operators = {
            "equals", "not_equals", "contains", "not_contains",
            "starts_with", "ends_with", "matches_regex", "matches_glob",
            "greater_than", "less_than", "greater_or_equal", "less_or_equal",
            "between", "is_today", "is_this_week", "within_last",
            "not_within_last", "before", "after", "in_list", "not_in_list",
            "is_true", "is_false", "exists", "not_exists",
            "is_empty", "is_not_empty",
        }
        for t in get_templates():
            for cond in t.get("conditions", []):
                op = cond.get("operator", "")
                assert op in valid_operators, f"Template '{t['name']}' has invalid operator: {op}"

    def test_all_actions_have_valid_types(self):
        """Verify all template actions use valid action types."""
        valid_types = {
            "move", "copy", "rename", "delete", "trash", "archive", "extract",
            "add_tags", "remove_tags", "set_tags", "set_comment", "set_label",
            "open_with", "import_to_photos", "import_to_music",
            "run_shell", "run_applescript", "run_automator", "run_shortcut",
            "notify", "nothing", "sort_into_subfolder", "make_alias",
            "toggle_lock", "toggle_extension", "reveal_in_finder",
        }
        for t in get_templates():
            for action in t.get("actions", []):
                atype = action.get("action_type", "")
                assert atype in valid_types, f"Template '{t['name']}' has invalid action: {atype}"
