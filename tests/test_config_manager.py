"""
Tests for the ConfigManager.

Verifies configuration loading, saving, backup/restore, import/export,
and edge cases like missing files and corrupt data.
"""

import json
import os
import tempfile
import pytest
from pathlib import Path

import yaml

from sortmeout.config.manager import ConfigManager
from sortmeout.config.settings import Settings


@pytest.fixture
def config_dir():
    """Create a temporary config directory."""
    dir_path = tempfile.mkdtemp()
    yield dir_path
    # Cleanup
    import shutil

    shutil.rmtree(dir_path, ignore_errors=True)


@pytest.fixture
def config_path(config_dir):
    """Return path to a config file in the temp directory."""
    return os.path.join(config_dir, "config.yaml")


@pytest.fixture
def manager(config_path):
    """Create a ConfigManager with a temp config file."""
    return ConfigManager(config_path=config_path)


class TestConfigManagerCreation:
    """Verify ConfigManager initialization."""

    def test_create_with_custom_path(self, config_path):
        mgr = ConfigManager(config_path=config_path)
        assert mgr.config_path == Path(config_path)

    def test_creates_config_directory(self, config_dir):
        nested = os.path.join(config_dir, "deep", "nested", "config.yaml")
        mgr = ConfigManager(config_path=nested)
        assert mgr.config_dir.exists()

    def test_creates_backup_directory(self, manager):
        assert manager.backup_dir.exists()


class TestConfigLoad:
    """Verify configuration loading."""

    def test_load_returns_defaults_when_no_file(self, manager):
        config = manager.load_config()
        assert "folders" in config
        assert isinstance(config["folders"], list)
        assert "_metadata" in config

    def test_load_yaml_config(self, manager):
        test_config = {
            "folders": [{"path": "/tmp/test", "rules": []}],
        }
        with open(manager.config_path, "w") as f:
            yaml.safe_dump(test_config, f)

        config = manager.load_config()
        assert len(config["folders"]) == 1
        assert config["folders"][0]["path"] == "/tmp/test"

    def test_load_json_config(self, config_dir):
        json_path = os.path.join(config_dir, "config.json")
        test_config = {"folders": [{"path": "/tmp/test"}]}
        with open(json_path, "w") as f:
            json.dump(test_config, f)

        mgr = ConfigManager(config_path=json_path)
        config = mgr.load_config()
        assert config["folders"][0]["path"] == "/tmp/test"

    def test_load_corrupt_file_returns_defaults(self, manager):
        with open(manager.config_path, "w") as f:
            f.write("{{invalid yaml: [[[")

        config = manager.load_config()
        # Should fall back to defaults, not crash
        assert "folders" in config


class TestConfigSave:
    """Verify configuration saving."""

    def test_save_creates_file(self, manager):
        config = {"folders": [{"path": "/tmp/save_test"}]}
        result = manager.save_config(config)
        assert result is True
        assert manager.config_path.exists()

    def test_save_adds_metadata(self, manager):
        config = {"folders": []}
        manager.save_config(config)

        loaded = manager.load_config()
        assert "_metadata" in loaded
        assert "version" in loaded["_metadata"]
        assert "updated_at" in loaded["_metadata"]

    def test_save_roundtrip_preserves_data(self, manager):
        config = {
            "folders": [
                {"path": "/tmp/alpha", "rules": [{"name": "test_rule"}]},
                {"path": "/tmp/beta", "rules": []},
            ]
        }
        manager.save_config(config)
        loaded = manager.load_config()
        assert len(loaded["folders"]) == 2
        assert loaded["folders"][0]["path"] == "/tmp/alpha"
        assert loaded["folders"][0]["rules"][0]["name"] == "test_rule"

    def test_save_creates_backup_of_existing(self, manager):
        # Save initial config
        manager.save_config({"folders": []})
        # Save again — this should trigger a backup
        manager.save_config({"folders": [{"path": "/tmp/backup_test"}]})

        backups = manager.list_backups()
        assert len(backups) >= 1


class TestConfigBackup:
    """Verify backup and restore functionality."""

    def test_list_backups_empty_initially(self, manager):
        backups = manager.list_backups()
        assert backups == []

    def test_restore_nonexistent_backup_returns_false(self, manager):
        result = manager.restore_backup("nonexistent_backup.yaml")
        assert result is False

    def test_restore_no_backups_returns_false(self, manager):
        result = manager.restore_backup()
        assert result is False

    def test_backup_and_restore_roundtrip(self, manager):
        original = {"folders": [{"path": "/tmp/original"}]}
        manager.save_config(original)

        # Overwrite with different config
        manager.save_config({"folders": [{"path": "/tmp/overwritten"}]})

        # Restore from backup (should be the original)
        result = manager.restore_backup()
        assert result is True

        restored = manager.load_config()
        assert restored["folders"][0]["path"] == "/tmp/original"

    def test_cleanup_keeps_only_n_backups(self, manager):
        # Create 15 backups by saving 15 times
        manager.save_config({"folders": []})
        for i in range(15):
            manager.save_config({"folders": [{"path": f"/tmp/{i}"}]})

        backups = manager.list_backups()
        assert len(backups) <= 10


class TestConfigExportImport:
    """Verify export and import functionality."""

    def test_export_yaml(self, manager, config_dir):
        manager.save_config({"folders": [{"path": "/tmp/export"}]})

        output = os.path.join(config_dir, "exported.yaml")
        result = manager.export_config(output, format="yaml")
        assert result is True
        assert os.path.exists(output)

        with open(output) as f:
            exported = yaml.safe_load(f)
        assert exported["folders"][0]["path"] == "/tmp/export"

    def test_export_json(self, manager, config_dir):
        manager.save_config({"folders": [{"path": "/tmp/export_json"}]})

        output = os.path.join(config_dir, "exported.json")
        result = manager.export_config(output, format="json")
        assert result is True

        with open(output) as f:
            exported = json.load(f)
        assert exported["folders"][0]["path"] == "/tmp/export_json"

    def test_import_replaces_config(self, manager, config_dir):
        # Create an import file
        import_path = os.path.join(config_dir, "import.yaml")
        with open(import_path, "w") as f:
            yaml.safe_dump({"folders": [{"path": "/tmp/imported"}]}, f)

        result = manager.import_config(import_path, merge=False)
        assert result is True

        config = manager.load_config()
        assert config["folders"][0]["path"] == "/tmp/imported"

    def test_import_merge_combines_folders(self, manager, config_dir):
        # Save initial config
        manager.save_config({"folders": [{"path": "/tmp/existing"}]})

        # Create import file with different folder
        import_path = os.path.join(config_dir, "merge.yaml")
        with open(import_path, "w") as f:
            yaml.safe_dump({"folders": [{"path": "/tmp/new_folder"}]}, f)

        result = manager.import_config(import_path, merge=True)
        assert result is True

        config = manager.load_config()
        paths = [f["path"] for f in config["folders"]]
        assert "/tmp/existing" in paths
        assert "/tmp/new_folder" in paths

    def test_import_nonexistent_file_returns_false(self, manager):
        result = manager.import_config("/nonexistent/path.yaml")
        assert result is False


class TestConfigReset:
    """Verify config reset."""

    def test_reset_returns_to_defaults(self, manager):
        manager.save_config({"folders": [{"path": "/tmp/pre_reset"}]})
        result = manager.reset_config()
        assert result is True

        config = manager.load_config()
        assert config["folders"] == []

    def test_reset_creates_backup_first(self, manager):
        manager.save_config({"folders": [{"path": "/tmp/pre_reset"}]})
        manager.reset_config()

        backups = manager.list_backups()
        assert len(backups) >= 1


class TestSettings:
    """Verify Settings load/save via ConfigManager."""

    def test_load_default_settings(self, manager):
        settings = manager.load_settings()
        assert isinstance(settings, Settings)

    def test_save_and_load_settings(self, manager):
        settings = Settings()
        result = manager.save_settings(settings)
        assert result is True

        loaded = manager.load_settings()
        assert isinstance(loaded, Settings)
