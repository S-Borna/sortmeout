"""
Native macOS Settings window for SortMeOut.

Provides a tabbed preferences window (General, Watcher, Trash,
Notifications, Logging, Advanced) built with AppKit/PyObjC.
"""

from __future__ import annotations

import threading
from typing import Callable, Optional

try:
    import AppKit
    import objc
    from Foundation import NSObject, NSMakeRect, NSMakeSize
except ImportError:
    AppKit = None

from sortmeout.config.manager import ConfigManager
from sortmeout.config.settings import (
    Settings,
    TrashSettings,
    NotificationSettings,
    LoggingSettings,
    WatcherSettings,
)
from sortmeout.utils.logger import get_logger

logger = get_logger(__name__)

# Window dimensions
WIN_WIDTH = 520
WIN_HEIGHT = 440
PADDING = 20
LABEL_WIDTH = 200
CONTROL_X = LABEL_WIDTH + PADDING + 10
CONTROL_WIDTH = 240


def show_settings_window(
    config_manager: ConfigManager,
    on_change: Optional[Callable] = None,
) -> None:
    """Show the settings window on the main thread."""
    if AppKit is None:
        raise ImportError("AppKit (PyObjC) is required for the settings window.")

    def _open():
        try:
            win = SettingsWindow(config_manager, on_change)
            win.show()
        except Exception as e:
            logger.error("Failed to open settings window: %s", e)

    if threading.current_thread() is threading.main_thread():
        _open()
    else:
        AppKit.NSApp.performSelectorOnMainThread_withObject_waitUntilDone_(
            objc.selector(lambda self: _open(), signature=b"v@:"), None, False,
        )


class SettingsWindow:
    """Native macOS settings window with tabs."""

    def __init__(
        self,
        config_manager: ConfigManager,
        on_change: Optional[Callable] = None,
    ):
        self._config_manager = config_manager
        self._on_change = on_change
        self._settings: Settings = config_manager.load_settings()
        self._controls: dict = {}

        self._build_window()

    # ──────────────────────────────────────────────────────────────

    def _build_window(self) -> None:
        """Build the native settings window."""
        style = (
            AppKit.NSWindowStyleMaskTitled
            | AppKit.NSWindowStyleMaskClosable
            | AppKit.NSWindowStyleMaskMiniaturizable
        )
        self._window = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(200, 200, WIN_WIDTH, WIN_HEIGHT),
            style,
            AppKit.NSBackingStoreBuffered,
            False,
        )
        self._window.setTitle_("SortMeOut Settings")
        self._window.setMinSize_(NSMakeSize(WIN_WIDTH, WIN_HEIGHT))
        self._window.center()

        content = self._window.contentView()

        # Tab view
        tab_view = AppKit.NSTabView.alloc().initWithFrame_(
            NSMakeRect(10, 50, WIN_WIDTH - 20, WIN_HEIGHT - 60)
        )

        tabs = [
            ("General", self._build_general_tab),
            ("Watcher", self._build_watcher_tab),
            ("Trash", self._build_trash_tab),
            ("Notifications", self._build_notifications_tab),
            ("Logging", self._build_logging_tab),
            ("Advanced", self._build_advanced_tab),
        ]

        for title, builder in tabs:
            item = AppKit.NSTabViewItem.alloc().initWithIdentifier_(title)
            item.setLabel_(title)
            view = builder()
            item.setView_(view)
            tab_view.addTabViewItem_(item)

        content.addSubview_(tab_view)

        # Save / Cancel buttons
        save_btn = AppKit.NSButton.alloc().initWithFrame_(
            NSMakeRect(WIN_WIDTH - 100, 10, 80, 30)
        )
        save_btn.setTitle_("Save")
        save_btn.setBezelStyle_(AppKit.NSBezelStyleRounded)
        save_btn.setTarget_(self)
        save_btn.setAction_(objc.selector(self._on_save, signature=b"v@:@"))
        save_btn.setKeyEquivalent_("\r")
        content.addSubview_(save_btn)

        cancel_btn = AppKit.NSButton.alloc().initWithFrame_(
            NSMakeRect(WIN_WIDTH - 190, 10, 80, 30)
        )
        cancel_btn.setTitle_("Cancel")
        cancel_btn.setBezelStyle_(AppKit.NSBezelStyleRounded)
        cancel_btn.setTarget_(self)
        cancel_btn.setAction_(objc.selector(self._on_cancel, signature=b"v@:@"))
        cancel_btn.setKeyEquivalent_("\x1b")
        content.addSubview_(cancel_btn)

    # ──────────────────────────────────────────────────────────────
    # TAB BUILDERS
    # ──────────────────────────────────────────────────────────────

    def _build_general_tab(self) -> AppKit.NSView:
        """Build the General settings tab."""
        view = AppKit.NSView.alloc().initWithFrame_(
            NSMakeRect(0, 0, WIN_WIDTH - 40, WIN_HEIGHT - 100)
        )
        y = WIN_HEIGHT - 150

        self._add_checkbox(view, "start_at_login", "Start at Login",
                           self._settings.start_at_login, y)
        y -= 30
        self._add_checkbox(view, "show_menu_bar_icon", "Show Menu Bar Icon",
                           self._settings.show_menu_bar_icon, y)
        y -= 30
        self._add_checkbox(view, "preview_mode", "Preview Mode (log only, no actions)",
                           self._settings.preview_mode, y)
        y -= 30
        self._add_checkbox(view, "confirm_destructive", "Confirm Destructive Actions",
                           self._settings.confirm_destructive_actions, y)
        y -= 40
        self._add_popup(view, "theme", "Theme:", ["system", "light", "dark"],
                        self._settings.theme, y)
        y -= 40
        self._add_popup(view, "language", "Language:", ["en", "sv"],
                        self._settings.language, y)

        return view

    def _build_watcher_tab(self) -> AppKit.NSView:
        """Build the Watcher settings tab."""
        view = AppKit.NSView.alloc().initWithFrame_(
            NSMakeRect(0, 0, WIN_WIDTH - 40, WIN_HEIGHT - 100)
        )
        y = WIN_HEIGHT - 150
        ws = self._settings.watcher

        self._add_number_field(view, "watcher_latency", "Latency (seconds):",
                               ws.latency_seconds, y)
        y -= 40
        self._add_number_field(view, "watcher_debounce", "Debounce (seconds):",
                               ws.debounce_seconds, y)
        y -= 40
        self._add_checkbox(view, "watcher_ignore_hidden", "Ignore Hidden Files",
                           ws.ignore_hidden_files, y)
        y -= 30
        self._add_checkbox(view, "watcher_ignore_system", "Ignore System Files",
                           ws.ignore_system_files, y)
        y -= 40
        self._add_text_field(view, "watcher_ignore_patterns", "Ignore Patterns (comma-separated):",
                             ", ".join(ws.custom_ignore_patterns), y, height=60)

        return view

    def _build_trash_tab(self) -> AppKit.NSView:
        """Build the Trash settings tab."""
        view = AppKit.NSView.alloc().initWithFrame_(
            NSMakeRect(0, 0, WIN_WIDTH - 40, WIN_HEIGHT - 100)
        )
        y = WIN_HEIGHT - 150
        ts = self._settings.trash

        self._add_checkbox(view, "trash_enabled", "Enable Trash Management",
                           ts.enabled, y)
        y -= 40
        self._add_number_field(view, "trash_max_age", "Max Age (days):",
                               ts.max_age_days, y)
        y -= 40
        self._add_number_field(view, "trash_max_size", "Max Size (GB):",
                               ts.max_size_gb, y)
        y -= 40
        self._add_checkbox(view, "trash_app_sweep", "App Sweep (clean leftover files)",
                           ts.app_sweep_enabled, y)
        y -= 30
        self._add_checkbox(view, "trash_app_prompt", "Ask Before Cleaning App Files",
                           ts.app_sweep_prompt, y)

        return view

    def _build_notifications_tab(self) -> AppKit.NSView:
        """Build the Notifications settings tab."""
        view = AppKit.NSView.alloc().initWithFrame_(
            NSMakeRect(0, 0, WIN_WIDTH - 40, WIN_HEIGHT - 100)
        )
        y = WIN_HEIGHT - 150
        ns = self._settings.notifications

        self._add_checkbox(view, "notif_enabled", "Enable Notifications",
                           ns.enabled, y)
        y -= 30
        self._add_checkbox(view, "notif_rule_matches", "Show Rule Matches",
                           ns.show_rule_matches, y)
        y -= 30
        self._add_checkbox(view, "notif_errors", "Show Errors",
                           ns.show_errors, y)
        y -= 30
        self._add_checkbox(view, "notif_summary", "Show Summary",
                           ns.show_summary, y)
        y -= 30
        self._add_checkbox(view, "notif_sound", "Enable Sound",
                           ns.sound_enabled, y)
        y -= 40
        self._add_number_field(view, "notif_interval", "Summary Interval (minutes):",
                               ns.summary_interval_minutes, y)

        return view

    def _build_logging_tab(self) -> AppKit.NSView:
        """Build the Logging settings tab."""
        view = AppKit.NSView.alloc().initWithFrame_(
            NSMakeRect(0, 0, WIN_WIDTH - 40, WIN_HEIGHT - 100)
        )
        y = WIN_HEIGHT - 150
        ls = self._settings.logging

        self._add_popup(view, "log_level", "Log Level:",
                        ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        ls.level, y)
        y -= 40
        self._add_checkbox(view, "log_file", "Enable File Logging",
                           ls.file_logging, y)
        y -= 30
        self._add_checkbox(view, "log_actions", "Log All Actions",
                           ls.action_logging, y)
        y -= 40
        self._add_number_field(view, "log_max_size", "Max Log Size (MB):",
                               ls.max_log_size_mb, y)
        y -= 40
        self._add_number_field(view, "log_backup_count", "Backup Count:",
                               ls.backup_count, y)

        return view

    def _build_advanced_tab(self) -> AppKit.NSView:
        """Build the Advanced settings tab."""
        view = AppKit.NSView.alloc().initWithFrame_(
            NSMakeRect(0, 0, WIN_WIDTH - 40, WIN_HEIGHT - 100)
        )
        y = WIN_HEIGHT - 150

        self._add_number_field(view, "max_concurrent", "Max Concurrent Actions:",
                               self._settings.max_concurrent_actions, y)
        y -= 40
        self._add_number_field(view, "action_timeout", "Action Timeout (seconds):",
                               self._settings.action_timeout_seconds, y)
        y -= 40
        self._add_checkbox(view, "retry_failed", "Retry Failed Actions",
                           self._settings.retry_failed_actions, y)
        y -= 40
        self._add_number_field(view, "retry_count", "Retry Count:",
                               self._settings.retry_count, y)
        y -= 30
        self._add_checkbox(view, "show_preview_hover", "Show Preview on Hover",
                           self._settings.show_preview_on_hover, y)

        return view

    # ──────────────────────────────────────────────────────────────
    # CONTROL HELPERS
    # ──────────────────────────────────────────────────────────────

    def _add_checkbox(
        self, view: AppKit.NSView, key: str, title: str, value: bool, y: int,
    ) -> None:
        """Add a checkbox control."""
        btn = AppKit.NSButton.alloc().initWithFrame_(
            NSMakeRect(PADDING, y, WIN_WIDTH - 60, 22)
        )
        btn.setButtonType_(AppKit.NSSwitchButton)
        btn.setTitle_(title)
        btn.setState_(AppKit.NSOnState if value else AppKit.NSOffState)
        view.addSubview_(btn)
        self._controls[key] = ("checkbox", btn)

    def _add_number_field(
        self, view: AppKit.NSView, key: str, label: str, value, y: int,
    ) -> None:
        """Add a labeled number field."""
        lbl = AppKit.NSTextField.labelWithString_(label)
        lbl.setFrame_(NSMakeRect(PADDING, y, LABEL_WIDTH, 22))
        view.addSubview_(lbl)

        field = AppKit.NSTextField.alloc().initWithFrame_(
            NSMakeRect(CONTROL_X, y, 100, 22)
        )
        field.setStringValue_(str(value))
        view.addSubview_(field)
        self._controls[key] = ("number", field)

    def _add_text_field(
        self, view: AppKit.NSView, key: str, label: str, value: str, y: int,
        height: int = 22,
    ) -> None:
        """Add a labeled text field (optionally multi-line)."""
        lbl = AppKit.NSTextField.labelWithString_(label)
        lbl.setFrame_(NSMakeRect(PADDING, y + height - 22, LABEL_WIDTH, 22))
        view.addSubview_(lbl)

        field = AppKit.NSTextField.alloc().initWithFrame_(
            NSMakeRect(CONTROL_X, y, CONTROL_WIDTH, height)
        )
        field.setStringValue_(value)
        view.addSubview_(field)
        self._controls[key] = ("text", field)

    def _add_popup(
        self, view: AppKit.NSView, key: str, label: str,
        options: list, current: str, y: int,
    ) -> None:
        """Add a labeled popup button (dropdown)."""
        lbl = AppKit.NSTextField.labelWithString_(label)
        lbl.setFrame_(NSMakeRect(PADDING, y, LABEL_WIDTH, 22))
        view.addSubview_(lbl)

        popup = AppKit.NSPopUpButton.alloc().initWithFrame_pullsDown_(
            NSMakeRect(CONTROL_X, y, CONTROL_WIDTH, 26), False,
        )
        for opt in options:
            popup.addItemWithTitle_(opt)

        if current in options:
            popup.selectItemWithTitle_(current)

        view.addSubview_(popup)
        self._controls[key] = ("popup", popup)

    # ──────────────────────────────────────────────────────────────
    # READ VALUES BACK
    # ──────────────────────────────────────────────────────────────

    def _get_bool(self, key: str) -> bool:
        """Read a checkbox value."""
        kind, ctrl = self._controls[key]
        return ctrl.state() == AppKit.NSOnState

    def _get_int(self, key: str) -> int:
        """Read an integer field."""
        kind, ctrl = self._controls[key]
        try:
            return int(ctrl.stringValue())
        except (ValueError, TypeError):
            return 0

    def _get_float(self, key: str) -> float:
        """Read a float field."""
        kind, ctrl = self._controls[key]
        try:
            return float(ctrl.stringValue())
        except (ValueError, TypeError):
            return 0.0

    def _get_str(self, key: str) -> str:
        """Read a text/popup value."""
        kind, ctrl = self._controls[key]
        if kind == "popup":
            selected = ctrl.selectedItem()
            return selected.title() if selected else ""
        return ctrl.stringValue()

    def _collect_settings(self) -> Settings:
        """Collect all control values into a Settings object."""
        return Settings(
            # General
            start_at_login=self._get_bool("start_at_login"),
            show_menu_bar_icon=self._get_bool("show_menu_bar_icon"),
            preview_mode=self._get_bool("preview_mode"),
            confirm_destructive_actions=self._get_bool("confirm_destructive"),
            theme=self._get_str("theme"),
            language=self._get_str("language"),
            show_preview_on_hover=self._get_bool("show_preview_hover"),
            # Watcher
            watcher=WatcherSettings(
                latency_seconds=self._get_float("watcher_latency"),
                debounce_seconds=self._get_float("watcher_debounce"),
                ignore_hidden_files=self._get_bool("watcher_ignore_hidden"),
                ignore_system_files=self._get_bool("watcher_ignore_system"),
                custom_ignore_patterns=[
                    p.strip()
                    for p in self._get_str("watcher_ignore_patterns").split(",")
                    if p.strip()
                ],
            ),
            # Trash
            trash=TrashSettings(
                enabled=self._get_bool("trash_enabled"),
                max_age_days=self._get_int("trash_max_age"),
                max_size_gb=self._get_float("trash_max_size"),
                app_sweep_enabled=self._get_bool("trash_app_sweep"),
                app_sweep_prompt=self._get_bool("trash_app_prompt"),
            ),
            # Notifications
            notifications=NotificationSettings(
                enabled=self._get_bool("notif_enabled"),
                show_rule_matches=self._get_bool("notif_rule_matches"),
                show_errors=self._get_bool("notif_errors"),
                show_summary=self._get_bool("notif_summary"),
                sound_enabled=self._get_bool("notif_sound"),
                summary_interval_minutes=self._get_int("notif_interval"),
            ),
            # Logging
            logging=LoggingSettings(
                level=self._get_str("log_level"),
                file_logging=self._get_bool("log_file"),
                action_logging=self._get_bool("log_actions"),
                max_log_size_mb=self._get_int("log_max_size"),
                backup_count=self._get_int("log_backup_count"),
            ),
            # Advanced
            max_concurrent_actions=self._get_int("max_concurrent"),
            action_timeout_seconds=self._get_int("action_timeout"),
            retry_failed_actions=self._get_bool("retry_failed"),
            retry_count=self._get_int("retry_count"),
        )

    # ──────────────────────────────────────────────────────────────
    # ACTIONS
    # ──────────────────────────────────────────────────────────────

    def _on_save(self, sender) -> None:
        """Save settings and close."""
        try:
            settings = self._collect_settings()
            self._config_manager.save_settings(settings)

            # Handle Launch at Login toggle
            try:
                from sortmeout.macos.launchd import set_launch_at_login
                set_launch_at_login(settings.start_at_login)
            except Exception as e:
                logger.warning("Could not update Launch at Login: %s", e)

            if self._on_change:
                self._on_change(settings)
            logger.info("Settings saved successfully")
            self._window.close()
        except Exception as e:
            logger.error("Failed to save settings: %s", e)
            alert = AppKit.NSAlert.alloc().init()
            alert.setMessageText_("Error Saving Settings")
            alert.setInformativeText_(str(e))
            alert.runModal()

    def _on_cancel(self, sender) -> None:
        """Close without saving."""
        self._window.close()

    def show(self) -> None:
        """Show the settings window."""
        self._window.makeKeyAndOrderFront_(None)
        AppKit.NSApp.activateIgnoringOtherApps_(True)
