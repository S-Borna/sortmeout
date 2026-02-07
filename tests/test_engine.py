"""
Tests for the RuleEngine class.
"""

import os
import shutil
import tempfile
import pytest
from pathlib import Path

from sortmeout.core.engine import RuleEngine, BatchProcessor, ProcessingResult
from sortmeout.core.rule import Rule, RuleMatchMode as MatchMode
from sortmeout.core.condition import Condition
from sortmeout.core.action import Action


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    dir_path = tempfile.mkdtemp()
    yield dir_path
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)


@pytest.fixture
def engine():
    """Create a RuleEngine instance."""
    return RuleEngine()


@pytest.fixture
def sample_rules():
    """Create sample rules for testing."""
    return [
        Rule(
            name="Move TXT files",
            conditions=[Condition("extension", "equals", "txt")],
            actions=[Action("move", destination="~/Documents/Text")],
            priority=1,
        ),
        Rule(
            name="Move PDF files",
            conditions=[Condition("extension", "equals", "pdf")],
            actions=[Action("move", destination="~/Documents/PDF")],
            priority=2,
        ),
        Rule(
            name="Archive old files",
            conditions=[
                Condition("extension", "in_list", ["txt", "pdf"]),
                Condition("date_modified", "not_within_last", "30 days"),
            ],
            actions=[Action("archive", format="zip")],
            priority=3,
        ),
    ]


class TestRuleEngineCreation:
    """Tests for RuleEngine creation."""

    def test_create_engine(self):
        engine = RuleEngine()
        assert engine is not None
        assert engine.rules == []

    def test_create_engine_with_rules(self, sample_rules):
        engine = RuleEngine(rules=sample_rules)
        assert len(engine.rules) == 3


class TestRuleManagement:
    """Tests for rule management in the engine."""

    def test_add_rule(self, engine):
        rule = Rule(
            name="Test",
            conditions=[Condition("extension", "equals", "txt")],
            actions=[Action("move", destination="~/Documents")],
        )

        engine.add_rule(rule)

        assert len(engine.rules) == 1
        assert engine.rules[0] == rule

    def test_remove_rule(self, engine):
        rule = Rule(name="Test")
        engine.add_rule(rule)

        engine.remove_rule(rule.id)

        assert len(engine.rules) == 0

    def test_get_rule_by_id(self, engine, sample_rules):
        for rule in sample_rules:
            engine.add_rule(rule)

        rule = engine.get_rule(sample_rules[1].id)

        assert rule is not None
        assert rule.name == "Move PDF files"

    def test_get_nonexistent_rule(self, engine):
        rule = engine.get_rule("nonexistent")
        assert rule is None

    def test_enable_disable_rule(self, engine):
        rule = Rule(name="Test")
        engine.add_rule(rule)

        engine.disable_rule(rule.id)
        assert not engine.rules[0].enabled

        engine.enable_rule(rule.id)
        assert engine.rules[0].enabled


class TestRulePriority:
    """Tests for rule priority ordering."""

    def test_rules_sorted_by_priority(self, engine, sample_rules):
        for rule in sample_rules:
            engine.add_rule(rule)

        # Should be sorted by priority (highest first)
        sorted_rules = engine.get_rules_sorted()

        assert sorted_rules[0].priority >= sorted_rules[1].priority
        assert sorted_rules[1].priority >= sorted_rules[2].priority

    def test_reorder_rules(self, engine, sample_rules):
        for rule in sample_rules:
            engine.add_rule(rule)

        # Change priority
        engine.set_rule_priority(sample_rules[0].id, 10)

        sorted_rules = engine.get_rules_sorted()
        assert sorted_rules[0].name == "Move TXT files"


class TestFileMatching:
    """Tests for file matching against rules."""

    def test_find_matching_rules(self, engine, sample_rules):
        for rule in sample_rules:
            engine.add_rule(rule)

        file_info = {"extension": "txt", "name": "test"}
        matching = engine.find_matching_rules(file_info)

        assert len(matching) >= 1
        assert any(r.name == "Move TXT files" for r in matching)

    def test_no_matching_rules(self, engine, sample_rules):
        for rule in sample_rules:
            engine.add_rule(rule)

        file_info = {"extension": "mp3", "name": "song"}
        matching = engine.find_matching_rules(file_info)

        assert len(matching) == 0

    def test_multiple_matching_rules(self, engine):
        engine.add_rule(Rule(
            name="All TXT",
            conditions=[Condition("extension", "equals", "txt")],
            actions=[Action("add_tags", tags=["text"])],
        ))
        engine.add_rule(Rule(
            name="Large files",
            conditions=[Condition("size", "greater_than", "1 KB")],
            actions=[Action("add_tags", tags=["large"])],
        ))

        file_info = {"extension": "txt", "size": 10000}
        matching = engine.find_matching_rules(file_info)

        assert len(matching) == 2


class TestFileProcessing:
    """Tests for file processing."""

    def test_process_file(self, engine, temp_dir):
        dest_dir = os.path.join(temp_dir, "destination")
        os.makedirs(dest_dir)

        # Create test file
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("Content")

        engine.add_rule(Rule(
            name="Move TXT",
            conditions=[Condition("extension", "equals", "txt")],
            actions=[Action("move", destination=dest_dir)],
        ))

        result = engine.process_file(test_file)

        assert result.success
        assert not os.path.exists(test_file)
        assert os.path.exists(os.path.join(dest_dir, "test.txt"))

    def test_process_file_no_match(self, engine, temp_dir):
        test_file = os.path.join(temp_dir, "test.pdf")
        with open(test_file, "w") as f:
            f.write("Content")

        engine.add_rule(Rule(
            name="Move TXT",
            conditions=[Condition("extension", "equals", "txt")],
            actions=[Action("move", destination=temp_dir)],
        ))

        result = engine.process_file(test_file)

        assert not result.matched
        assert os.path.exists(test_file)

    def test_process_file_preview_mode(self, engine, temp_dir):
        dest_dir = os.path.join(temp_dir, "destination")
        os.makedirs(dest_dir)

        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("Content")

        engine.add_rule(Rule(
            name="Move TXT",
            conditions=[Condition("extension", "equals", "txt")],
            actions=[Action("move", destination=dest_dir)],
        ))

        result = engine.process_file(test_file, preview=True)

        assert result.matched
        assert os.path.exists(test_file)  # File not actually moved


class TestStopProcessing:
    """Tests for stop_processing flag."""

    def test_stop_after_first_match(self, engine, temp_dir):
        dest_dir = os.path.join(temp_dir, "destination")
        os.makedirs(dest_dir)

        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("Content")

        # Add two rules that both match
        engine.add_rule(Rule(
            name="Rule 1",
            conditions=[Condition("extension", "equals", "txt")],
            actions=[Action("add_tags", tags=["rule1"])],
        ))
        engine.add_rule(Rule(
            name="Rule 2",
            conditions=[Condition("extension", "equals", "txt")],
            actions=[Action("add_tags", tags=["rule2"])],
        ))

        result = engine.process_file(test_file)

        # Only first rule should be applied
        assert result.rules_applied == 1


class TestRulePreview:
    """Tests for rule preview functionality."""

    def test_preview_rule(self, engine, temp_dir):
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("Content")

        rule = Rule(
            name="Move TXT",
            conditions=[Condition("extension", "equals", "txt")],
            actions=[Action("move", destination=temp_dir)],
        )

        preview = engine.preview_rule(rule, test_file)

        assert preview["matches"]
        assert len(preview["actions"]) == 1
        assert os.path.exists(test_file)  # File not modified


class TestBatchProcessor:
    """Tests for BatchProcessor."""

    def test_process_directory(self, temp_dir):
        dest_dir = os.path.join(temp_dir, "destination")
        os.makedirs(dest_dir)

        # Create test files
        for name in ["file1.txt", "file2.txt", "file3.pdf"]:
            with open(os.path.join(temp_dir, name), "w") as f:
                f.write("Content")

        engine = RuleEngine()
        engine.add_rule(Rule(
            name="Move TXT",
            conditions=[Condition("extension", "equals", "txt")],
            actions=[Action("move", destination=dest_dir)],
        ))

        processor = BatchProcessor(engine)
        results = processor.process_directory(temp_dir)

        assert results["total"] == 3
        assert results["matched"] == 2
        assert results["processed"] == 2

    def test_process_with_filters(self, temp_dir):
        # Create test files
        for name in ["file1.txt", "file2.txt", "image.png"]:
            with open(os.path.join(temp_dir, name), "w") as f:
                f.write("Content")

        engine = RuleEngine()
        processor = BatchProcessor(engine)

        # Only process .txt files
        results = processor.process_directory(
            temp_dir,
            extensions=[".txt"]
        )

        assert results["total"] == 2

    def test_batch_process_recursive(self, temp_dir):
        # Create subdirectory with files
        subdir = os.path.join(temp_dir, "subdir")
        os.makedirs(subdir)

        with open(os.path.join(temp_dir, "root.txt"), "w") as f:
            f.write("Root")
        with open(os.path.join(subdir, "sub.txt"), "w") as f:
            f.write("Sub")

        engine = RuleEngine()
        processor = BatchProcessor(engine)

        results = processor.process_directory(temp_dir, recursive=True)

        assert results["total"] == 2


class TestProcessingResult:
    """Tests for ProcessingResult."""

    def test_success_result(self):
        result = ProcessingResult(
            file_path="/path/to/file.txt",
            matched_rules=["TestRule"],
        )

        assert result.success
        assert result.matched
        assert result.rules_applied == 1

    def test_failure_result(self):
        result = ProcessingResult(
            file_path="/path/to/file.txt",
            matched_rules=["TestRule"],
            errors=["Permission denied"],
        )

        assert not result.success
        assert result.errors[0] == "Permission denied"


class TestEngineStatistics:
    """Tests for engine statistics."""

    def test_stats_tracking(self, engine, temp_dir):
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, "w") as f:
            f.write("Content")

        engine.add_rule(Rule(
            name="Move TXT",
            conditions=[Condition("extension", "equals", "txt")],
            actions=[Action("add_tags", tags=["test"])],
        ))

        engine.process_file(test_file)

        stats = engine.get_stats()

        assert stats["total_processed"] >= 1
        assert stats["total_matched"] >= 1


class TestEngineSerialization:
    """Tests for engine serialization."""

    def test_export_rules(self, engine, sample_rules, temp_dir):
        for rule in sample_rules:
            engine.add_rule(rule)

        export_path = os.path.join(temp_dir, "rules.yaml")
        engine.export_rules(export_path)

        assert os.path.exists(export_path)

    def test_import_rules(self, engine, sample_rules, temp_dir):
        # First export
        for rule in sample_rules:
            engine.add_rule(rule)

        export_path = os.path.join(temp_dir, "rules.yaml")
        engine.export_rules(export_path)

        # Create new engine and import
        new_engine = RuleEngine()
        new_engine.import_rules(export_path)

        assert len(new_engine.rules) == len(sample_rules)
