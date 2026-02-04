"""
Tests for the Condition class.
"""

import pytest
from datetime import datetime, timedelta

from sortmeout.core.condition import (
    Condition,
    ConditionGroup,
    ConditionGroupMode,
    ConditionOperator,
    ConditionAttribute,
    parse_size,
    parse_duration,
    name_equals,
    name_contains,
    extension_is,
    extension_in,
    size_greater_than,
    size_less_than,
    modified_within,
)


class TestParseSize:
    """Tests for size parsing."""

    def test_parse_bytes(self):
        assert parse_size("1024") == 1024
        assert parse_size("1024B") == 1024

    def test_parse_kilobytes(self):
        assert parse_size("1KB") == 1024
        assert parse_size("1K") == 1024
        assert parse_size("10KB") == 10240

    def test_parse_megabytes(self):
        assert parse_size("1MB") == 1024 ** 2
        assert parse_size("1M") == 1024 ** 2
        assert parse_size("5MB") == 5 * 1024 ** 2

    def test_parse_gigabytes(self):
        assert parse_size("1GB") == 1024 ** 3
        assert parse_size("2GB") == 2 * 1024 ** 3

    def test_parse_with_spaces(self):
        assert parse_size(" 10 MB ") == 10 * 1024 ** 2

    def test_parse_float(self):
        assert parse_size("1.5MB") == int(1.5 * 1024 ** 2)


class TestParseDuration:
    """Tests for duration parsing."""

    def test_parse_days(self):
        assert parse_duration("7 days") == timedelta(days=7)
        assert parse_duration("7d") == timedelta(days=7)

    def test_parse_hours(self):
        assert parse_duration("24 hours") == timedelta(hours=24)
        assert parse_duration("24h") == timedelta(hours=24)

    def test_parse_minutes(self):
        assert parse_duration("30 minutes") == timedelta(minutes=30)
        assert parse_duration("30m") == timedelta(minutes=30)

    def test_parse_weeks(self):
        assert parse_duration("2 weeks") == timedelta(weeks=2)
        assert parse_duration("2w") == timedelta(weeks=2)


class TestConditionEquality:
    """Tests for equality-based conditions."""

    def test_equals_case_insensitive(self):
        cond = Condition("name", "equals", "Test")
        assert cond.evaluate({"name": "test"}) is True
        assert cond.evaluate({"name": "TEST"}) is True
        assert cond.evaluate({"name": "other"}) is False

    def test_equals_case_sensitive(self):
        cond = Condition("name", "equals", "Test", case_sensitive=True)
        assert cond.evaluate({"name": "Test"}) is True
        assert cond.evaluate({"name": "test"}) is False

    def test_not_equals(self):
        cond = Condition("name", "not_equals", "Test")
        assert cond.evaluate({"name": "other"}) is True
        assert cond.evaluate({"name": "test"}) is False


class TestConditionContains:
    """Tests for contains-based conditions."""

    def test_contains(self):
        cond = Condition("name", "contains", "report")
        assert cond.evaluate({"name": "monthly_report_2024"}) is True
        assert cond.evaluate({"name": "invoice_2024"}) is False

    def test_not_contains(self):
        cond = Condition("name", "not_contains", "temp")
        assert cond.evaluate({"name": "document.pdf"}) is True
        assert cond.evaluate({"name": "temp_file.txt"}) is False

    def test_starts_with(self):
        cond = Condition("name", "starts_with", "Invoice")
        assert cond.evaluate({"name": "Invoice_2024"}) is True
        assert cond.evaluate({"name": "2024_Invoice"}) is False

    def test_ends_with(self):
        cond = Condition("name", "ends_with", "_final")
        assert cond.evaluate({"name": "document_final"}) is True
        assert cond.evaluate({"name": "final_document"}) is False


class TestConditionPatternMatching:
    """Tests for pattern matching conditions."""

    def test_matches_regex(self):
        cond = Condition("name", "matches_regex", r"^invoice_\d{4}$")
        assert cond.evaluate({"name": "invoice_2024"}) is True
        assert cond.evaluate({"name": "invoice_abc"}) is False

    def test_matches_glob(self):
        cond = Condition("name", "matches_glob", "report_*.pdf")
        assert cond.evaluate({"name": "report_2024.pdf"}) is True
        assert cond.evaluate({"name": "report_january.pdf"}) is True
        assert cond.evaluate({"name": "invoice_2024.pdf"}) is False


class TestConditionNumeric:
    """Tests for numeric conditions."""

    def test_greater_than(self):
        cond = Condition("size", "greater_than", 1024)
        assert cond.evaluate({"size": 2048}) is True
        assert cond.evaluate({"size": 512}) is False

    def test_greater_than_with_size_string(self):
        cond = Condition("size", "greater_than", "1MB")
        assert cond.evaluate({"size": 2 * 1024 * 1024}) is True
        assert cond.evaluate({"size": 512 * 1024}) is False

    def test_less_than(self):
        cond = Condition("size", "less_than", "10MB")
        assert cond.evaluate({"size": 5 * 1024 * 1024}) is True
        assert cond.evaluate({"size": 20 * 1024 * 1024}) is False

    def test_between(self):
        cond = Condition("size", "between", [1024, 4096])
        assert cond.evaluate({"size": 2048}) is True
        assert cond.evaluate({"size": 512}) is False
        assert cond.evaluate({"size": 8192}) is False


class TestConditionDate:
    """Tests for date-based conditions."""

    def test_is_today(self):
        cond = Condition("date_modified", "is_today", None)
        assert cond.evaluate({"date_modified": datetime.now()}) is True
        assert cond.evaluate({"date_modified": datetime.now() - timedelta(days=1)}) is False

    def test_is_yesterday(self):
        cond = Condition("date_modified", "is_yesterday", None)
        assert cond.evaluate({"date_modified": datetime.now() - timedelta(days=1)}) is True
        assert cond.evaluate({"date_modified": datetime.now()}) is False

    def test_within_last(self):
        cond = Condition("date_modified", "within_last", "7 days")
        assert cond.evaluate({"date_modified": datetime.now() - timedelta(days=3)}) is True
        assert cond.evaluate({"date_modified": datetime.now() - timedelta(days=10)}) is False

    def test_not_within_last(self):
        cond = Condition("date_modified", "not_within_last", "30 days")
        assert cond.evaluate({"date_modified": datetime.now() - timedelta(days=60)}) is True
        assert cond.evaluate({"date_modified": datetime.now() - timedelta(days=7)}) is False


class TestConditionList:
    """Tests for list-based conditions."""

    def test_in_list(self):
        cond = Condition("extension", "in_list", ["pdf", "doc", "docx"])
        assert cond.evaluate({"extension": "pdf"}) is True
        assert cond.evaluate({"extension": "txt"}) is False

    def test_not_in_list(self):
        cond = Condition("extension", "not_in_list", ["tmp", "temp", "bak"])
        assert cond.evaluate({"extension": "pdf"}) is True
        assert cond.evaluate({"extension": "tmp"}) is False


class TestConditionExistence:
    """Tests for existence conditions."""

    def test_exists(self):
        cond = Condition("tags", "exists", None)
        assert cond.evaluate({"tags": ["work"]}) is True
        assert cond.evaluate({"tags": None}) is False
        assert cond.evaluate({}) is False

    def test_not_exists(self):
        cond = Condition("tags", "not_exists", None)
        assert cond.evaluate({}) is True
        assert cond.evaluate({"tags": None}) is True
        assert cond.evaluate({"tags": ["work"]}) is False

    def test_is_empty(self):
        cond = Condition("tags", "is_empty", None)
        assert cond.evaluate({"tags": []}) is True
        assert cond.evaluate({"tags": ""}) is True
        assert cond.evaluate({"tags": ["work"]}) is False

    def test_is_not_empty(self):
        cond = Condition("tags", "is_not_empty", None)
        assert cond.evaluate({"tags": ["work"]}) is True
        assert cond.evaluate({"tags": []}) is False


class TestConditionNegation:
    """Tests for negated conditions."""

    def test_negated_equals(self):
        cond = Condition("extension", "equals", "pdf", negate=True)
        assert cond.evaluate({"extension": "pdf"}) is False
        assert cond.evaluate({"extension": "doc"}) is True

    def test_negated_contains(self):
        cond = Condition("name", "contains", "temp", negate=True)
        assert cond.evaluate({"name": "temp_file"}) is False
        assert cond.evaluate({"name": "document"}) is True


class TestConditionGroup:
    """Tests for condition groups."""

    def test_all_mode(self):
        group = ConditionGroup(
            conditions=[
                Condition("extension", "equals", "pdf"),
                Condition("size", "greater_than", "1MB"),
            ],
            mode=ConditionGroupMode.ALL,
        )

        # Both conditions match
        assert group.evaluate({"extension": "pdf", "size": 2 * 1024 * 1024}) is True

        # Only one condition matches
        assert group.evaluate({"extension": "pdf", "size": 512 * 1024}) is False

    def test_any_mode(self):
        group = ConditionGroup(
            conditions=[
                Condition("extension", "equals", "pdf"),
                Condition("extension", "equals", "doc"),
            ],
            mode=ConditionGroupMode.ANY,
        )

        assert group.evaluate({"extension": "pdf"}) is True
        assert group.evaluate({"extension": "doc"}) is True
        assert group.evaluate({"extension": "txt"}) is False

    def test_none_mode(self):
        group = ConditionGroup(
            conditions=[
                Condition("extension", "equals", "tmp"),
                Condition("extension", "equals", "temp"),
            ],
            mode=ConditionGroupMode.NONE,
        )

        assert group.evaluate({"extension": "pdf"}) is True
        assert group.evaluate({"extension": "tmp"}) is False

    def test_nested_groups(self):
        inner_group = ConditionGroup(
            conditions=[
                Condition("extension", "equals", "pdf"),
                Condition("extension", "equals", "doc"),
            ],
            mode=ConditionGroupMode.ANY,
        )

        outer_group = ConditionGroup(
            conditions=[
                inner_group,
                Condition("size", "greater_than", "1MB"),
            ],
            mode=ConditionGroupMode.ALL,
        )

        # PDF larger than 1MB
        assert outer_group.evaluate({"extension": "pdf", "size": 2 * 1024 * 1024}) is True

        # PDF smaller than 1MB
        assert outer_group.evaluate({"extension": "pdf", "size": 512 * 1024}) is False


class TestConditionSerialization:
    """Tests for condition serialization."""

    def test_to_dict(self):
        cond = Condition("extension", "equals", "pdf", case_sensitive=True)
        data = cond.to_dict()

        assert data["attribute"] == "extension"
        assert data["operator"] == "equals"
        assert data["value"] == "pdf"
        assert data["case_sensitive"] is True

    def test_from_dict(self):
        data = {
            "attribute": "name",
            "operator": "contains",
            "value": "report",
            "case_sensitive": False,
        }

        cond = Condition.from_dict(data)
        assert cond.evaluate({"name": "monthly_report"}) is True

    def test_condition_group_serialization(self):
        group = ConditionGroup(
            conditions=[
                Condition("extension", "equals", "pdf"),
                Condition("size", "greater_than", 1024),
            ],
            mode=ConditionGroupMode.ALL,
        )

        data = group.to_dict()
        restored = ConditionGroup.from_dict(data)

        assert len(restored.conditions) == 2
        assert restored.mode == ConditionGroupMode.ALL


class TestConvenienceFunctions:
    """Tests for condition convenience functions."""

    def test_name_equals(self):
        cond = name_equals("document")
        assert cond.evaluate({"name": "Document"}) is True

    def test_name_contains(self):
        cond = name_contains("report")
        assert cond.evaluate({"name": "monthly_report_2024"}) is True

    def test_extension_is(self):
        cond = extension_is(".pdf")  # With dot
        assert cond.evaluate({"extension": "pdf"}) is True

        cond = extension_is("pdf")  # Without dot
        assert cond.evaluate({"extension": "pdf"}) is True

    def test_extension_in(self):
        cond = extension_in(["pdf", "doc", "docx"])
        assert cond.evaluate({"extension": "pdf"}) is True
        assert cond.evaluate({"extension": "txt"}) is False

    def test_size_greater_than(self):
        cond = size_greater_than("5MB")
        assert cond.evaluate({"size": 10 * 1024 * 1024}) is True

    def test_size_less_than(self):
        cond = size_less_than("1MB")
        assert cond.evaluate({"size": 512 * 1024}) is True

    def test_modified_within(self):
        cond = modified_within("7 days")
        assert cond.evaluate({"date_modified": datetime.now() - timedelta(days=3)}) is True
