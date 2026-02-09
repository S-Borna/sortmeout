"""
Import smoke tests for SortMeOut.

Verifies that every module in the package can be imported without errors.
This catches broken imports, missing dependencies, and circular imports —
the most common regressions after refactoring.
"""

import importlib
import pytest


class TestCoreImports:
    """Verify all core modules import cleanly."""

    def test_import_sortmeout_root(self):
        import sortmeout
        assert hasattr(sortmeout, "__version__")
        assert hasattr(sortmeout, "SortMeOut")
        assert hasattr(sortmeout, "Rule")
        assert hasattr(sortmeout, "Condition")
        assert hasattr(sortmeout, "Action")

    def test_import_core_rule(self):
        from sortmeout.core.rule import Rule
        assert Rule is not None

    def test_import_core_condition(self):
        from sortmeout.core.condition import Condition, ConditionGroup
        assert Condition is not None
        assert ConditionGroup is not None

    def test_import_core_action(self):
        from sortmeout.core.action import Action, ActionType, ActionResult
        assert Action is not None
        assert ActionType is not None

    def test_import_core_engine(self):
        from sortmeout.core.engine import RuleEngine
        assert RuleEngine is not None

    def test_import_core_watcher(self):
        from sortmeout.core.watcher import FolderWatcher, WatcherManager
        assert FolderWatcher is not None
        assert WatcherManager is not None

    def test_import_core_history(self):
        from sortmeout.core.history import HistoryManager
        assert HistoryManager is not None

    def test_import_core_scheduler(self):
        from sortmeout.core.scheduler import Scheduler, ScheduledRule
        assert Scheduler is not None
        assert ScheduledRule is not None

    def test_import_core_templates(self):
        from sortmeout.core.templates import get_templates
        assert callable(get_templates)

    def test_import_core_license(self):
        from sortmeout.core.license import LicenseAuthority
        assert LicenseAuthority is not None


class TestConfigImports:
    """Verify config modules import cleanly."""

    def test_import_config_manager(self):
        from sortmeout.config.manager import ConfigManager
        assert ConfigManager is not None

    def test_import_config_settings(self):
        from sortmeout.config.settings import Settings
        assert Settings is not None


class TestUtilImports:
    """Verify utility modules import cleanly."""

    def test_import_file_info(self):
        from sortmeout.utils.file_info import get_file_info
        assert callable(get_file_info)

    def test_import_logger(self):
        from sortmeout.utils.logger import get_logger, setup_logging
        assert callable(get_logger)
        assert callable(setup_logging)


class TestMacOSImports:
    """Verify macOS integration modules import cleanly."""

    def test_import_spotlight(self):
        from sortmeout.macos.spotlight import search_spotlight, get_metadata
        assert callable(search_spotlight)
        assert callable(get_metadata)

    def test_import_tags(self):
        from sortmeout.macos import tags
        assert hasattr(tags, "get_tags") or hasattr(tags, "set_tags")

    def test_import_trash(self):
        from sortmeout.macos.trash import TrashManager
        assert TrashManager is not None

    def test_import_system(self):
        from sortmeout.macos import system
        assert system is not None

    def test_import_launchd(self):
        from sortmeout.macos import launchd
        assert launchd is not None


class TestIntegrationImports:
    """Verify all integration modules import cleanly."""

    def test_import_mail(self):
        from sortmeout.integrations.mail import MailIntegration
        assert MailIntegration is not None

    def test_import_calendar(self):
        from sortmeout.integrations.calendar import CalendarIntegration
        assert CalendarIntegration is not None

    def test_import_messages(self):
        from sortmeout.integrations.messages import MessagesIntegration
        assert MessagesIntegration is not None

    def test_import_contacts(self):
        from sortmeout.integrations.contacts import ContactsIntegration
        assert ContactsIntegration is not None

    def test_import_notes(self):
        from sortmeout.integrations.notes import NotesIntegration
        assert NotesIntegration is not None

    def test_import_presentations(self):
        from sortmeout.integrations.presentations import PresentationBuilder
        assert PresentationBuilder is not None

    def test_import_images(self):
        from sortmeout.integrations.images import ImageEditor, ImageGenerator
        assert ImageEditor is not None
        assert ImageGenerator is not None

    def test_import_monitor(self):
        from sortmeout.integrations.monitor import ProactiveMonitor
        assert ProactiveMonitor is not None

    def test_import_learner(self):
        from sortmeout.integrations.learner import BehaviorLearner
        assert BehaviorLearner is not None

    def test_import_integrations_package(self):
        """Verify the integrations __init__.py re-exports work."""
        from sortmeout.integrations import (
            MailIntegration,
            CalendarIntegration,
            MessagesIntegration,
            ContactsIntegration,
            PresentationBuilder,
            NotesIntegration,
            ProactiveMonitor,
            BehaviorLearner,
            ImageEditor,
            ImageGenerator,
        )
        assert MailIntegration is not None


class TestAIImports:
    """Verify AI module imports cleanly."""

    def test_import_ai_assistant(self):
        from sortmeout.ai.assistant import FileAssistant
        assert FileAssistant is not None


class TestGUIImports:
    """Verify GUI module lazy imports work."""

    def test_gui_lazy_import_main(self):
        from sortmeout.gui import main
        assert callable(main)

    def test_gui_lazy_import_menubarapp(self):
        from sortmeout.gui import MenuBarApp
        assert MenuBarApp is not None

    def test_gui_lazy_import_show_chat_window(self):
        from sortmeout.gui import show_chat_window
        assert callable(show_chat_window)

    def test_gui_lazy_import_show_image_window(self):
        from sortmeout.gui import show_image_window
        assert callable(show_image_window)

    def test_gui_lazy_import_show_rule_editor(self):
        from sortmeout.gui import show_rule_editor
        assert callable(show_rule_editor)

    def test_gui_invalid_attribute_raises(self):
        import sortmeout.gui as gui_mod
        with pytest.raises(AttributeError):
            _ = gui_mod.nonexistent_thing


class TestCLIImport:
    """Verify CLI module imports and Click group is valid."""

    def test_import_cli_main(self):
        from sortmeout.cli import main
        assert main is not None

    def test_cli_is_click_group(self):
        from sortmeout.cli import main
        import click
        assert isinstance(main, click.Group)
