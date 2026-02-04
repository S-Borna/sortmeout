"""
Tests for the Action class.
"""

import os
import shutil
import tempfile
import pytest
from pathlib import Path

from sortmeout.core.action import (
    Action,
    ActionType,
    ActionResult,
    move_to,
    copy_to,
    rename,
    delete,
    trash,
    archive,
    add_tags,
    notify,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    dir_path = tempfile.mkdtemp()
    yield dir_path
    # Cleanup
    if os.path.exists(dir_path):
        shutil.rmtree(dir_path)


@pytest.fixture
def test_file(temp_dir):
    """Create a test file."""
    file_path = os.path.join(temp_dir, "test_file.txt")
    with open(file_path, "w") as f:
        f.write("Test content")
    return file_path


@pytest.fixture
def file_info(test_file):
    """Generate basic file info dict."""
    path = Path(test_file)
    return {
        "path": str(path),
        "name": path.stem,
        "extension": path.suffix.lstrip("."),
        "full_name": path.name,
        "parent_folder": path.parent.name,
    }


class TestActionCreation:
    """Tests for action creation."""

    def test_create_with_type_string(self):
        action = Action("move", destination="~/Documents")
        assert action.action_type == ActionType.MOVE
        assert action.params["destination"] == "~/Documents"

    def test_create_with_type_enum(self):
        action = Action(ActionType.COPY, destination="~/Documents")
        assert action.action_type == ActionType.COPY

    def test_action_has_unique_id(self):
        action1 = Action("move", destination="~/Documents")
        action2 = Action("move", destination="~/Documents")
        assert action1.id != action2.id


class TestMoveAction:
    """Tests for move action."""

    def test_move_to_directory(self, temp_dir, test_file, file_info):
        dest_dir = os.path.join(temp_dir, "destination")
        os.makedirs(dest_dir)

        action = Action("move", destination=dest_dir)
        result = action.execute(test_file, file_info)

        assert result.success
        assert not os.path.exists(test_file)
        assert os.path.exists(os.path.join(dest_dir, "test_file.txt"))

    def test_move_creates_destination(self, temp_dir, test_file, file_info):
        dest_dir = os.path.join(temp_dir, "new_folder", "subfolder")

        action = Action("move", destination=dest_dir)
        result = action.execute(test_file, file_info)

        assert result.success
        assert os.path.exists(os.path.join(dest_dir, "test_file.txt"))

    def test_move_handles_conflict_rename(self, temp_dir, test_file, file_info):
        dest_dir = os.path.join(temp_dir, "destination")
        os.makedirs(dest_dir)

        # Create existing file
        existing = os.path.join(dest_dir, "test_file.txt")
        with open(existing, "w") as f:
            f.write("Existing")

        action = Action("move", destination=dest_dir, if_exists="rename")
        result = action.execute(test_file, file_info)

        assert result.success
        assert os.path.exists(existing)  # Original still exists
        assert "test_file (1).txt" in result.destination_path

    def test_move_preview_mode(self, test_file, file_info):
        action = Action("move", destination="~/Documents")
        result = action.execute(test_file, file_info, preview=True)

        assert result.success
        assert os.path.exists(test_file)  # File not actually moved
        assert "PREVIEW" in result.message


class TestCopyAction:
    """Tests for copy action."""

    def test_copy_to_directory(self, temp_dir, test_file, file_info):
        dest_dir = os.path.join(temp_dir, "destination")
        os.makedirs(dest_dir)

        action = Action("copy", destination=dest_dir)
        result = action.execute(test_file, file_info)

        assert result.success
        assert os.path.exists(test_file)  # Original still exists
        assert os.path.exists(os.path.join(dest_dir, "test_file.txt"))

    def test_copy_preserves_metadata(self, temp_dir, test_file, file_info):
        dest_dir = os.path.join(temp_dir, "destination")
        os.makedirs(dest_dir)

        action = Action("copy", destination=dest_dir)
        result = action.execute(test_file, file_info)

        original_stat = os.stat(test_file)
        copy_stat = os.stat(result.destination_path)

        assert original_stat.st_mode == copy_stat.st_mode


class TestRenameAction:
    """Tests for rename action."""

    def test_rename_file(self, temp_dir, test_file, file_info):
        action = Action("rename", new_name="renamed_file.txt")
        result = action.execute(test_file, file_info)

        assert result.success
        assert not os.path.exists(test_file)
        assert os.path.exists(os.path.join(temp_dir, "renamed_file.txt"))

    def test_rename_with_variables(self, temp_dir, test_file, file_info):
        action = Action("rename", new_name="{name}_processed.{extension}")
        result = action.execute(test_file, file_info)

        assert result.success
        assert "test_file_processed.txt" in result.destination_path

    def test_rename_handles_conflict(self, temp_dir, test_file, file_info):
        # Create a file with the target name
        target = os.path.join(temp_dir, "target.txt")
        with open(target, "w") as f:
            f.write("Existing")

        action = Action("rename", new_name="target.txt", if_exists="rename")
        result = action.execute(test_file, file_info)

        assert result.success
        assert "target (1).txt" in result.destination_path


class TestDeleteAction:
    """Tests for delete action."""

    def test_delete_file(self, test_file, file_info):
        action = Action("delete", force=True)
        result = action.execute(test_file, file_info)

        assert result.success
        assert not os.path.exists(test_file)

    def test_delete_directory(self, temp_dir, file_info):
        dir_to_delete = os.path.join(temp_dir, "to_delete")
        os.makedirs(dir_to_delete)

        # Add some files
        with open(os.path.join(dir_to_delete, "file.txt"), "w") as f:
            f.write("Content")

        action = Action("delete", force=True)
        result = action.execute(dir_to_delete, {"path": dir_to_delete})

        assert result.success
        assert not os.path.exists(dir_to_delete)


class TestArchiveAction:
    """Tests for archive action."""

    def test_archive_zip(self, temp_dir, test_file, file_info):
        action = Action("archive", format="zip")
        result = action.execute(test_file, file_info)

        assert result.success
        assert os.path.exists(test_file)  # Original still exists
        assert result.destination_path.endswith(".zip")

    def test_archive_delete_original(self, temp_dir, test_file, file_info):
        action = Action("archive", format="zip", delete_original=True)
        result = action.execute(test_file, file_info)

        assert result.success
        assert not os.path.exists(test_file)


class TestVariableExpansion:
    """Tests for variable expansion in action parameters."""

    def test_expand_name(self, test_file, file_info):
        action = Action("rename", new_name="prefix_{name}.txt")
        result = action.execute(test_file, file_info, preview=True)

        assert "prefix_test_file.txt" in str(result.metadata.get("params", {}).get("new_name", ""))

    def test_expand_extension(self, test_file, file_info):
        action = Action("rename", new_name="file.{extension}")
        result = action.execute(test_file, file_info, preview=True)

        params = result.metadata.get("params", {})
        assert "file.txt" in str(params.get("new_name", ""))

    def test_expand_date(self, test_file, file_info):
        from datetime import datetime

        action = Action("rename", new_name="{name}_{date}.txt")
        result = action.execute(test_file, file_info, preview=True)

        today = datetime.now().strftime("%Y-%m-%d")
        params = result.metadata.get("params", {})
        assert today in str(params.get("new_name", ""))


class TestActionSerialization:
    """Tests for action serialization."""

    def test_to_dict(self):
        action = Action(
            "move",
            destination="~/Documents",
            enabled=True,
            stop_on_error=False,
        )

        data = action.to_dict()

        assert data["action_type"] == "move"
        assert data["params"]["destination"] == "~/Documents"
        assert data["enabled"] is True
        assert data["stop_on_error"] is False

    def test_from_dict(self):
        data = {
            "action_type": "copy",
            "params": {"destination": "~/Backup"},
            "enabled": True,
        }

        action = Action.from_dict(data)

        assert action.action_type == ActionType.COPY
        assert action.params["destination"] == "~/Backup"

    def test_duplicate(self):
        original = Action("move", destination="~/Documents")
        duplicate = original.duplicate()

        assert duplicate.action_type == original.action_type
        assert duplicate.params == original.params
        assert duplicate.id != original.id


class TestConvenienceFunctions:
    """Tests for action convenience functions."""

    def test_move_to(self):
        action = move_to("~/Documents")
        assert action.action_type == ActionType.MOVE
        assert action.params["destination"] == "~/Documents"

    def test_copy_to(self):
        action = copy_to("~/Backup")
        assert action.action_type == ActionType.COPY

    def test_rename(self):
        action = rename("new_name.txt")
        assert action.action_type == ActionType.RENAME
        assert action.params["new_name"] == "new_name.txt"

    def test_delete(self):
        action = delete(force=True)
        assert action.action_type == ActionType.DELETE
        assert action.params["force"] is True

    def test_trash(self):
        action = trash()
        assert action.action_type == ActionType.TRASH

    def test_archive(self):
        action = archive(format="zip", delete_original=True)
        assert action.action_type == ActionType.ARCHIVE
        assert action.params["format"] == "zip"
        assert action.params["delete_original"] is True

    def test_add_tags(self):
        action = add_tags("work", "important")
        assert action.action_type == ActionType.ADD_TAGS
        assert action.params["tags"] == ["work", "important"]


class TestActionResult:
    """Tests for ActionResult."""

    def test_success_result(self):
        result = ActionResult(
            success=True,
            action_type=ActionType.MOVE,
            source_path="/source/file.txt",
            destination_path="/dest/file.txt",
            message="Moved successfully",
        )

        assert result.success
        assert "✓" in str(result)

    def test_failure_result(self):
        result = ActionResult(
            success=False,
            action_type=ActionType.MOVE,
            source_path="/source/file.txt",
            error="Permission denied",
        )

        assert not result.success
        assert "✗" in str(result)
