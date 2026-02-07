"""Tests for the history/logging system."""

import json
import os
import tempfile
from datetime import datetime, timedelta

import pytest

from sortmeout.core.history import HistoryManager, HistoryEntry


@pytest.fixture
def history_db():
    """Create a temporary history database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    mgr = HistoryManager(db_path=db_path)
    yield mgr
    mgr.close()
    os.unlink(db_path)


class TestHistoryEntry:
    """Tests for HistoryEntry dataclass."""

    def test_create_entry(self):
        entry = HistoryEntry(
            action_type="move",
            source_path="/tmp/test.txt",
            destination_path="/tmp/docs/test.txt",
        )
        assert entry.action_type == "move"
        assert entry.success is True
        assert entry.timestamp != ""

    def test_source_name(self):
        entry = HistoryEntry(
            action_type="move",
            source_path="/Users/test/Documents/report.pdf",
        )
        assert entry.source_name == "report.pdf"

    def test_metadata_dict(self):
        entry = HistoryEntry(
            action_type="add_tags",
            source_path="/tmp/test.txt",
            metadata='{"tags": ["Important"]}',
        )
        assert entry.metadata_dict == {"tags": ["Important"]}

    def test_metadata_dict_empty(self):
        entry = HistoryEntry(action_type="move", source_path="/tmp/test.txt")
        assert entry.metadata_dict == {}


class TestHistoryManager:
    """Tests for HistoryManager."""

    def test_record_and_retrieve(self, history_db):
        entry_id = history_db.record(
            action_type="move",
            source_path="/tmp/test.txt",
            destination_path="/tmp/docs/test.txt",
            rule_name="Organize Docs",
        )
        assert entry_id > 0

        recent = history_db.get_recent(limit=1)
        assert len(recent) == 1
        assert recent[0].action_type == "move"
        assert recent[0].rule_name == "Organize Docs"

    def test_get_by_rule(self, history_db):
        history_db.record(action_type="move", source_path="/tmp/a.txt", rule_name="Rule A")
        history_db.record(action_type="copy", source_path="/tmp/b.txt", rule_name="Rule B")
        history_db.record(action_type="trash", source_path="/tmp/c.txt", rule_name="Rule A")

        results = history_db.get_by_rule("Rule A")
        assert len(results) == 2
        assert all(r.rule_name == "Rule A" for r in results)

    def test_get_by_action(self, history_db):
        history_db.record(action_type="move", source_path="/tmp/a.txt")
        history_db.record(action_type="move", source_path="/tmp/b.txt")
        history_db.record(action_type="copy", source_path="/tmp/c.txt")

        results = history_db.get_by_action("move")
        assert len(results) == 2

    def test_get_by_file(self, history_db):
        history_db.record(action_type="move", source_path="/tmp/test.txt", destination_path="/tmp/docs/test.txt")
        history_db.record(action_type="add_tags", source_path="/tmp/other.txt")

        results = history_db.get_by_file("/tmp/test.txt")
        assert len(results) == 1

        results = history_db.get_by_file("/tmp/docs/test.txt")
        assert len(results) == 1

    def test_get_errors(self, history_db):
        history_db.record(action_type="move", source_path="/tmp/a.txt", success=True)
        history_db.record(action_type="move", source_path="/tmp/b.txt", success=False, error="Permission denied")
        history_db.record(action_type="copy", source_path="/tmp/c.txt", success=False, error="Disk full")

        errors = history_db.get_errors()
        assert len(errors) == 2
        assert all(not e.success for e in errors)

    def test_search(self, history_db):
        history_db.record(action_type="move", source_path="/tmp/report.pdf", rule_name="PDF Rule")
        history_db.record(action_type="move", source_path="/tmp/photo.jpg", rule_name="Image Rule")

        results = history_db.search("report")
        assert len(results) == 1

        results = history_db.search("PDF")
        assert len(results) == 1

    def test_statistics(self, history_db):
        history_db.record(action_type="move", source_path="/tmp/a.txt", success=True, rule_name="R1")
        history_db.record(action_type="move", source_path="/tmp/b.txt", success=True, rule_name="R1")
        history_db.record(action_type="copy", source_path="/tmp/c.txt", success=False, rule_name="R2")

        stats = history_db.get_statistics(days=30)
        assert stats["total_actions"] == 3
        assert stats["successful"] == 2
        assert stats["errors"] == 1
        assert "move" in stats["by_action_type"]
        assert stats["by_action_type"]["move"] == 2
        assert "R1" in stats["by_rule"]

    def test_cleanup(self, history_db):
        # Record entries
        for i in range(10):
            history_db.record(action_type="move", source_path=f"/tmp/file{i}.txt")

        # Cleanup should keep all (they're recent)
        deleted = history_db.cleanup(max_age_days=1, max_entries=100)
        remaining = history_db.get_recent(limit=100)
        assert len(remaining) == 10

        # Cleanup with low max_entries
        deleted = history_db.cleanup(max_age_days=365, max_entries=5)
        remaining = history_db.get_recent(limit=100)
        assert len(remaining) == 5

    def test_export_json(self, history_db):
        history_db.record(action_type="move", source_path="/tmp/a.txt")
        history_db.record(action_type="copy", source_path="/tmp/b.txt")

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            export_path = f.name

        try:
            count = history_db.export_json(export_path)
            assert count == 2

            with open(export_path) as f:
                data = json.load(f)
            assert len(data) == 2
            assert data[0]["action_type"] in ("move", "copy")
        finally:
            os.unlink(export_path)
