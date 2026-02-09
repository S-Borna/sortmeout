"""
Tests for the CLI interface.

Verifies that CLI commands are registered, respond to --help,
and handle basic invocations correctly. These are characterization
tests that guard against regressions in the user-facing CLI surface.
"""

import pytest
from click.testing import CliRunner

from sortmeout.cli import main


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


class TestCLIMainGroup:
    """Verify the main CLI group and global options."""

    def test_main_help(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "SortMeOut" in result.output
        assert "Automated file organization" in result.output

    def test_main_version(self, runner):
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "SortMeOut" in result.output

    def test_main_no_args(self, runner):
        result = runner.invoke(main, [])
        # Click groups return exit code 2 when no subcommand given
        assert result.exit_code in (0, 2)
        assert "Usage" in result.output or "SortMeOut" in result.output


class TestCLISubcommands:
    """Verify all subcommands are registered and respond to --help."""

    @pytest.mark.parametrize(
        "command",
        [
            "start",
            "stop",
            "status",
            "test",
            "images",
        ],
    )
    def test_top_level_command_help(self, runner, command):
        result = runner.invoke(main, [command, "--help"])
        assert result.exit_code == 0, f"{command} --help failed: {result.output}"

    @pytest.mark.parametrize(
        "group",
        [
            "folder",
            "rule",
            "trash",
            "config",
            "license",
            "history",
            "template",
            "schedule",
        ],
    )
    def test_group_help(self, runner, group):
        result = runner.invoke(main, [group, "--help"])
        assert result.exit_code == 0, f"{group} --help failed: {result.output}"


class TestCLIFolderCommands:
    """Verify folder subcommands."""

    def test_folder_list(self, runner):
        result = runner.invoke(main, ["folder", "list"])
        # Should succeed even with no folders configured
        assert result.exit_code == 0

    def test_folder_add_help(self, runner):
        result = runner.invoke(main, ["folder", "add", "--help"])
        assert result.exit_code == 0
        assert "PATH" in result.output or "path" in result.output.lower()

    def test_folder_remove_help(self, runner):
        result = runner.invoke(main, ["folder", "remove", "--help"])
        assert result.exit_code == 0


class TestCLIRuleCommands:
    """Verify rule subcommands."""

    def test_rule_list_requires_folder(self, runner):
        result = runner.invoke(main, ["rule", "list", "--help"])
        assert result.exit_code == 0

    def test_rule_add_help(self, runner):
        result = runner.invoke(main, ["rule", "add", "--help"])
        assert result.exit_code == 0


class TestCLITrashCommands:
    """Verify trash subcommands."""

    def test_trash_status(self, runner):
        result = runner.invoke(main, ["trash", "status"])
        # Should work — reads system trash info
        assert result.exit_code == 0

    def test_trash_clean_help(self, runner):
        result = runner.invoke(main, ["trash", "clean", "--help"])
        assert result.exit_code == 0


class TestCLIConfigCommands:
    """Verify config subcommands."""

    def test_config_show(self, runner):
        result = runner.invoke(main, ["config", "show"])
        assert result.exit_code == 0

    def test_config_export_help(self, runner):
        result = runner.invoke(main, ["config", "export", "--help"])
        assert result.exit_code == 0


class TestCLITemplateCommands:
    """Verify template subcommands."""

    def test_template_list(self, runner):
        result = runner.invoke(main, ["template", "list"])
        assert result.exit_code == 0

    def test_template_show_help(self, runner):
        result = runner.invoke(main, ["template", "show", "--help"])
        assert result.exit_code == 0


class TestCLIHistoryCommands:
    """Verify history subcommands."""

    def test_history_list(self, runner):
        result = runner.invoke(main, ["history", "list"])
        assert result.exit_code == 0

    def test_history_stats(self, runner):
        result = runner.invoke(main, ["history", "stats"])
        assert result.exit_code == 0


class TestCLILicenseCommands:
    """Verify license subcommands."""

    def test_license_status(self, runner):
        result = runner.invoke(main, ["license", "status"])
        assert result.exit_code == 0

    def test_license_verify(self, runner):
        result = runner.invoke(main, ["license", "verify"])
        # May fail validation but should not crash
        assert result.exit_code in (0, 1)
