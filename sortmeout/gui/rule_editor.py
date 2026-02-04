"""
Rule Editor Window for SortMeOut.

A native macOS window for creating and editing automation rules.
Provides a visual interface for defining conditions and actions.
"""

import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable

try:
    from AppKit import (
        NSApplication, NSApp, NSWindow, NSWindowStyleMaskTitled,
        NSWindowStyleMaskClosable, NSWindowStyleMaskResizable,
        NSWindowStyleMaskMiniaturizable, NSBackingStoreBuffered,
        NSTableView, NSTableColumn, NSScrollView, NSButton,
        NSTextField, NSFont, NSColor, NSView, NSStackView,
        NSUserInterfaceLayoutOrientationVertical,
        NSUserInterfaceLayoutOrientationHorizontal,
        NSPopUpButton, NSComboBox, NSAlert, NSAlertStyleInformational,
        NSAlertStyleWarning, NSOpenPanel, NSSavePanel, NSModalResponseOK,
        NSBezelStyleRounded, NSTextFieldCell, NSTableViewSelectionHighlightStyleRegular,
        NSLayoutConstraint, NSBox, NSTitlePosition, NSLineBreakByTruncatingTail,
        NSControlStateValueOn, NSControlStateValueOff, NSSwitch,
        NSSegmentedControl, NSSegmentStyleRounded, NSImageNameAddTemplate,
        NSImageNameRemoveTemplate, NSImage,
    )
    from Foundation import (
        NSObject, NSRect, NSPoint, NSSize, NSMakeRect, 
        NSMutableArray, NSIndexSet, NSBundle
    )
    from objc import python_method
    HAS_APPKIT = True
except ImportError:
    HAS_APPKIT = False


# Import core modules
try:
    from sortmeout.core.condition import Condition, ConditionAttribute, ConditionOperator
    from sortmeout.core.action import Action, ActionType
    from sortmeout.core.rule import Rule, RuleMatchMode
except ImportError:
    # Fallback for standalone testing
    pass


# Condition options for UI
CONDITION_ATTRIBUTES = [
    ("name", "Name", "File name (without extension)"),
    ("extension", "Extension", "File extension"),
    ("full_name", "Full Name", "Name + extension"),
    ("size", "Size", "File size"),
    ("date_created", "Date Created", "When file was created"),
    ("date_modified", "Date Modified", "When file was last modified"),
    ("date_added", "Date Added", "When file was added (macOS)"),
    ("tags", "Tags", "Finder tags"),
    ("kind", "Kind", "File kind (e.g., PDF document)"),
    ("where_from", "Downloaded From", "Source URL for downloads"),
]

CONDITION_OPERATORS = {
    "string": [
        ("equals", "is"),
        ("not_equals", "is not"),
        ("contains", "contains"),
        ("not_contains", "does not contain"),
        ("starts_with", "starts with"),
        ("ends_with", "ends with"),
        ("matches_regex", "matches regex"),
        ("in_list", "is one of"),
    ],
    "numeric": [
        ("greater_than", "is greater than"),
        ("less_than", "is less than"),
        ("greater_or_equal", "is at least"),
        ("less_or_equal", "is at most"),
        ("between", "is between"),
    ],
    "date": [
        ("is_today", "is today"),
        ("is_this_week", "is this week"),
        ("within_last", "is within last"),
        ("not_within_last", "is not within last"),
        ("before", "is before"),
        ("after", "is after"),
    ],
    "list": [
        ("in_list", "includes"),
        ("not_in_list", "does not include"),
    ],
}

ACTION_TYPES = [
    ("move", "Move to Folder", "Move the file to a specified folder"),
    ("copy", "Copy to Folder", "Copy the file to a specified folder"),
    ("rename", "Rename", "Rename the file using a pattern"),
    ("trash", "Move to Trash", "Move the file to Trash"),
    ("add_tags", "Add Tags", "Add Finder tags"),
    ("remove_tags", "Remove Tags", "Remove Finder tags"),
    ("set_label", "Set Color Label", "Set Finder color label"),
    ("open_with", "Open With Application", "Open with a specific app"),
    ("archive", "Create Archive", "Compress into ZIP/TAR"),
    ("run_shell", "Run Shell Script", "Execute a shell command"),
    ("run_applescript", "Run AppleScript", "Execute AppleScript"),
    ("run_shortcut", "Run Shortcut", "Run a macOS Shortcut"),
    ("notify", "Show Notification", "Display a notification"),
]


if HAS_APPKIT:
    
    class ConditionRowView(NSView):
        """A row view for a single condition."""
        
        @classmethod
        def alloc_init_with_callback(cls, on_change: Callable, on_delete: Callable):
            self = cls.alloc().initWithFrame_(NSMakeRect(0, 0, 600, 36))
            self._on_change = on_change
            self._on_delete = on_delete
            self._setup_ui()
            return self
        
        @python_method
        def _setup_ui(self):
            # Attribute dropdown
            self.attribute_popup = NSPopUpButton.alloc().initWithFrame_(
                NSMakeRect(0, 4, 140, 28)
            )
            for attr, label, _ in CONDITION_ATTRIBUTES:
                self.attribute_popup.addItemWithTitle_(label)
            self.attribute_popup.setAction_("attributeChanged:")
            self.attribute_popup.setTarget_(self)
            self.addSubview_(self.attribute_popup)
            
            # Operator dropdown
            self.operator_popup = NSPopUpButton.alloc().initWithFrame_(
                NSMakeRect(148, 4, 160, 28)
            )
            self._update_operators("string")
            self.operator_popup.setAction_("operatorChanged:")
            self.operator_popup.setTarget_(self)
            self.addSubview_(self.operator_popup)
            
            # Value field
            self.value_field = NSTextField.alloc().initWithFrame_(
                NSMakeRect(316, 4, 200, 28)
            )
            self.value_field.setPlaceholderString_("Value")
            self.value_field.setTarget_(self)
            self.value_field.setAction_("valueChanged:")
            self.addSubview_(self.value_field)
            
            # Delete button
            self.delete_button = NSButton.alloc().initWithFrame_(
                NSMakeRect(524, 4, 28, 28)
            )
            self.delete_button.setImage_(NSImage.imageNamed_(NSImageNameRemoveTemplate))
            self.delete_button.setBezelStyle_(NSBezelStyleRounded)
            self.delete_button.setBordered_(False)
            self.delete_button.setTarget_(self)
            self.delete_button.setAction_("deleteClicked:")
            self.addSubview_(self.delete_button)
        
        @python_method
        def _update_operators(self, type_key: str):
            self.operator_popup.removeAllItems()
            operators = CONDITION_OPERATORS.get(type_key, CONDITION_OPERATORS["string"])
            for op_id, op_label in operators:
                self.operator_popup.addItemWithTitle_(op_label)
        
        def attributeChanged_(self, sender):
            idx = self.attribute_popup.indexOfSelectedItem()
            attr = CONDITION_ATTRIBUTES[idx][0]
            
            # Determine operator type based on attribute
            if attr in ("size", "size_bytes"):
                self._update_operators("numeric")
            elif attr in ("date_created", "date_modified", "date_added"):
                self._update_operators("date")
            elif attr in ("tags",):
                self._update_operators("list")
            else:
                self._update_operators("string")
            
            if self._on_change:
                self._on_change(self)
        
        def operatorChanged_(self, sender):
            if self._on_change:
                self._on_change(self)
        
        def valueChanged_(self, sender):
            if self._on_change:
                self._on_change(self)
        
        def deleteClicked_(self, sender):
            if self._on_delete:
                self._on_delete(self)
        
        @python_method
        def get_condition_data(self) -> Dict[str, Any]:
            attr_idx = self.attribute_popup.indexOfSelectedItem()
            op_idx = self.operator_popup.indexOfSelectedItem()
            
            attr = CONDITION_ATTRIBUTES[attr_idx][0]
            
            # Get current operator list
            if attr in ("size", "size_bytes"):
                ops = CONDITION_OPERATORS["numeric"]
            elif attr in ("date_created", "date_modified", "date_added"):
                ops = CONDITION_OPERATORS["date"]
            elif attr in ("tags",):
                ops = CONDITION_OPERATORS["list"]
            else:
                ops = CONDITION_OPERATORS["string"]
            
            operator = ops[op_idx][0] if op_idx < len(ops) else "equals"
            
            return {
                "attribute": attr,
                "operator": operator,
                "value": str(self.value_field.stringValue()),
            }


    class ActionRowView(NSView):
        """A row view for a single action."""
        
        @classmethod
        def alloc_init_with_callback(cls, on_change: Callable, on_delete: Callable):
            self = cls.alloc().initWithFrame_(NSMakeRect(0, 0, 600, 36))
            self._on_change = on_change
            self._on_delete = on_delete
            self._setup_ui()
            return self
        
        @python_method
        def _setup_ui(self):
            # Action type dropdown
            self.action_popup = NSPopUpButton.alloc().initWithFrame_(
                NSMakeRect(0, 4, 180, 28)
            )
            for action_id, label, _ in ACTION_TYPES:
                self.action_popup.addItemWithTitle_(label)
            self.action_popup.setAction_("actionChanged:")
            self.action_popup.setTarget_(self)
            self.addSubview_(self.action_popup)
            
            # Value/destination field
            self.value_field = NSTextField.alloc().initWithFrame_(
                NSMakeRect(188, 4, 250, 28)
            )
            self.value_field.setPlaceholderString_("Destination or value")
            self.value_field.setTarget_(self)
            self.value_field.setAction_("valueChanged:")
            self.addSubview_(self.value_field)
            
            # Browse button
            self.browse_button = NSButton.alloc().initWithFrame_(
                NSMakeRect(446, 4, 70, 28)
            )
            self.browse_button.setTitle_("Browse...")
            self.browse_button.setBezelStyle_(NSBezelStyleRounded)
            self.browse_button.setTarget_(self)
            self.browse_button.setAction_("browseClicked:")
            self.addSubview_(self.browse_button)
            
            # Delete button
            self.delete_button = NSButton.alloc().initWithFrame_(
                NSMakeRect(524, 4, 28, 28)
            )
            self.delete_button.setImage_(NSImage.imageNamed_(NSImageNameRemoveTemplate))
            self.delete_button.setBezelStyle_(NSBezelStyleRounded)
            self.delete_button.setBordered_(False)
            self.delete_button.setTarget_(self)
            self.delete_button.setAction_("deleteClicked:")
            self.addSubview_(self.delete_button)
            
            self._update_for_action_type(0)
        
        @python_method
        def _update_for_action_type(self, idx: int):
            action_id = ACTION_TYPES[idx][0]
            
            # Show/hide browse button based on action type
            needs_path = action_id in ("move", "copy", "open_with", "run_automator")
            self.browse_button.setHidden_(not needs_path)
            
            # Update placeholder
            placeholders = {
                "move": "Destination folder",
                "copy": "Destination folder",
                "rename": "Pattern (e.g., {date} - {name}.{ext})",
                "trash": "(no value needed)",
                "add_tags": "Tag names (comma-separated)",
                "remove_tags": "Tag names (comma-separated)",
                "set_label": "Color: None, Gray, Green, Purple, Blue, Yellow, Red, Orange",
                "open_with": "Application path",
                "archive": "Format: zip, tar, tar.gz",
                "run_shell": "Shell command",
                "run_applescript": "AppleScript code",
                "run_shortcut": "Shortcut name",
                "notify": "Notification message",
            }
            self.value_field.setPlaceholderString_(placeholders.get(action_id, "Value"))
            self.value_field.setEnabled_(action_id != "trash")
        
        def actionChanged_(self, sender):
            idx = self.action_popup.indexOfSelectedItem()
            self._update_for_action_type(idx)
            if self._on_change:
                self._on_change(self)
        
        def valueChanged_(self, sender):
            if self._on_change:
                self._on_change(self)
        
        def browseClicked_(self, sender):
            panel = NSOpenPanel.openPanel()
            panel.setCanChooseDirectories_(True)
            panel.setCanChooseFiles_(True)
            panel.setAllowsMultipleSelection_(False)
            
            if panel.runModal() == NSModalResponseOK:
                url = panel.URLs()[0]
                self.value_field.setStringValue_(url.path())
                if self._on_change:
                    self._on_change(self)
        
        def deleteClicked_(self, sender):
            if self._on_delete:
                self._on_delete(self)
        
        @python_method
        def get_action_data(self) -> Dict[str, Any]:
            idx = self.action_popup.indexOfSelectedItem()
            action_id = ACTION_TYPES[idx][0]
            value = str(self.value_field.stringValue())
            
            # Build params based on action type
            params = {}
            if action_id in ("move", "copy"):
                params["destination"] = value
            elif action_id == "rename":
                params["pattern"] = value
            elif action_id in ("add_tags", "remove_tags"):
                params["tags"] = [t.strip() for t in value.split(",") if t.strip()]
            elif action_id == "set_label":
                params["label"] = value
            elif action_id == "open_with":
                params["application"] = value
            elif action_id == "archive":
                params["format"] = value or "zip"
            elif action_id == "run_shell":
                params["command"] = value
            elif action_id == "run_applescript":
                params["script"] = value
            elif action_id == "run_shortcut":
                params["shortcut_name"] = value
            elif action_id == "notify":
                params["message"] = value
            
            return {
                "action_type": action_id,
                "params": params,
            }


    class RuleEditorWindowController(NSObject):
        """Controller for the Rule Editor window."""
        
        @classmethod
        def alloc_init_with_callback(cls, on_save: Optional[Callable] = None, 
                                      existing_rule: Optional[Dict] = None):
            self = cls.alloc().init()
            self._on_save = on_save
            self._existing_rule = existing_rule
            self._condition_rows = []
            self._action_rows = []
            self._create_window()
            return self
        
        @python_method
        def _create_window(self):
            """Create the main editor window."""
            # Window
            style = (NSWindowStyleMaskTitled | 
                     NSWindowStyleMaskClosable | 
                     NSWindowStyleMaskMiniaturizable |
                     NSWindowStyleMaskResizable)
            
            self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
                NSMakeRect(0, 0, 650, 600),
                style,
                NSBackingStoreBuffered,
                False
            )
            self.window.setTitle_("Edit Rule" if self._existing_rule else "New Rule")
            self.window.center()
            self.window.setMinSize_(NSSize(600, 500))
            
            content = self.window.contentView()
            content.setWantsLayer_(True)
            
            y_offset = 560
            
            # Rule name section
            name_label = NSTextField.labelWithString_("Rule Name:")
            name_label.setFrame_(NSMakeRect(20, y_offset, 100, 20))
            name_label.setFont_(NSFont.boldSystemFontOfSize_(13))
            content.addSubview_(name_label)
            
            y_offset -= 30
            self.name_field = NSTextField.alloc().initWithFrame_(
                NSMakeRect(20, y_offset, 610, 28)
            )
            self.name_field.setPlaceholderString_("Enter a descriptive name for this rule")
            content.addSubview_(self.name_field)
            
            # Description
            y_offset -= 35
            desc_label = NSTextField.labelWithString_("Description (optional):")
            desc_label.setFrame_(NSMakeRect(20, y_offset, 200, 20))
            content.addSubview_(desc_label)
            
            y_offset -= 30
            self.description_field = NSTextField.alloc().initWithFrame_(
                NSMakeRect(20, y_offset, 610, 28)
            )
            self.description_field.setPlaceholderString_("What does this rule do?")
            content.addSubview_(self.description_field)
            
            # Match mode
            y_offset -= 40
            match_label = NSTextField.labelWithString_("If:")
            match_label.setFrame_(NSMakeRect(20, y_offset, 30, 20))
            match_label.setFont_(NSFont.boldSystemFontOfSize_(13))
            content.addSubview_(match_label)
            
            self.match_popup = NSPopUpButton.alloc().initWithFrame_(
                NSMakeRect(50, y_offset - 4, 200, 28)
            )
            self.match_popup.addItemWithTitle_("All conditions match")
            self.match_popup.addItemWithTitle_("Any condition matches")
            self.match_popup.addItemWithTitle_("No conditions match")
            content.addSubview_(self.match_popup)
            
            # Conditions section
            y_offset -= 40
            cond_label = NSTextField.labelWithString_("Conditions:")
            cond_label.setFrame_(NSMakeRect(20, y_offset, 100, 20))
            cond_label.setFont_(NSFont.boldSystemFontOfSize_(13))
            content.addSubview_(cond_label)
            
            add_cond_btn = NSButton.alloc().initWithFrame_(
                NSMakeRect(560, y_offset - 4, 70, 28)
            )
            add_cond_btn.setTitle_("+ Add")
            add_cond_btn.setBezelStyle_(NSBezelStyleRounded)
            add_cond_btn.setTarget_(self)
            add_cond_btn.setAction_("addCondition:")
            content.addSubview_(add_cond_btn)
            
            # Conditions container
            y_offset -= 130
            self.conditions_container = NSView.alloc().initWithFrame_(
                NSMakeRect(20, y_offset, 610, 120)
            )
            self.conditions_container.setWantsLayer_(True)
            content.addSubview_(self.conditions_container)
            
            # Actions section
            y_offset -= 30
            actions_label = NSTextField.labelWithString_("Actions:")
            actions_label.setFrame_(NSMakeRect(20, y_offset, 100, 20))
            actions_label.setFont_(NSFont.boldSystemFontOfSize_(13))
            content.addSubview_(actions_label)
            
            add_action_btn = NSButton.alloc().initWithFrame_(
                NSMakeRect(560, y_offset - 4, 70, 28)
            )
            add_action_btn.setTitle_("+ Add")
            add_action_btn.setBezelStyle_(NSBezelStyleRounded)
            add_action_btn.setTarget_(self)
            add_action_btn.setAction_("addAction:")
            content.addSubview_(add_action_btn)
            
            # Actions container
            y_offset -= 130
            self.actions_container = NSView.alloc().initWithFrame_(
                NSMakeRect(20, y_offset, 610, 120)
            )
            self.actions_container.setWantsLayer_(True)
            content.addSubview_(self.actions_container)
            
            # Options section
            y_offset -= 40
            options_label = NSTextField.labelWithString_("Options:")
            options_label.setFrame_(NSMakeRect(20, y_offset, 100, 20))
            options_label.setFont_(NSFont.boldSystemFontOfSize_(13))
            content.addSubview_(options_label)
            
            y_offset -= 30
            self.continue_checkbox = NSButton.alloc().initWithFrame_(
                NSMakeRect(20, y_offset, 400, 20)
            )
            self.continue_checkbox.setButtonType_(3)  # Switch/checkbox
            self.continue_checkbox.setTitle_("Continue processing with next rules after matching")
            content.addSubview_(self.continue_checkbox)
            
            y_offset -= 25
            self.enabled_checkbox = NSButton.alloc().initWithFrame_(
                NSMakeRect(20, y_offset, 200, 20)
            )
            self.enabled_checkbox.setButtonType_(3)
            self.enabled_checkbox.setTitle_("Rule is enabled")
            self.enabled_checkbox.setState_(NSControlStateValueOn)
            content.addSubview_(self.enabled_checkbox)
            
            # Buttons at bottom
            cancel_btn = NSButton.alloc().initWithFrame_(
                NSMakeRect(460, 20, 80, 32)
            )
            cancel_btn.setTitle_("Cancel")
            cancel_btn.setBezelStyle_(NSBezelStyleRounded)
            cancel_btn.setTarget_(self)
            cancel_btn.setAction_("cancelClicked:")
            content.addSubview_(cancel_btn)
            
            save_btn = NSButton.alloc().initWithFrame_(
                NSMakeRect(550, 20, 80, 32)
            )
            save_btn.setTitle_("Save Rule")
            save_btn.setBezelStyle_(NSBezelStyleRounded)
            save_btn.setKeyEquivalent_("\r")  # Enter key
            save_btn.setTarget_(self)
            save_btn.setAction_("saveClicked:")
            content.addSubview_(save_btn)
            
            # Load existing rule if provided
            if self._existing_rule:
                self._load_existing_rule()
            else:
                # Add one default condition and action
                self.addCondition_(None)
                self.addAction_(None)
        
        @python_method
        def _load_existing_rule(self):
            """Load existing rule data into the editor."""
            rule = self._existing_rule
            
            self.name_field.setStringValue_(rule.get("name", ""))
            self.description_field.setStringValue_(rule.get("description", "") or "")
            
            # Match mode
            mode = rule.get("match_mode", "all")
            if mode == "all":
                self.match_popup.selectItemAtIndex_(0)
            elif mode == "any":
                self.match_popup.selectItemAtIndex_(1)
            else:
                self.match_popup.selectItemAtIndex_(2)
            
            # Options
            self.continue_checkbox.setState_(
                NSControlStateValueOn if rule.get("continue_processing") else NSControlStateValueOff
            )
            self.enabled_checkbox.setState_(
                NSControlStateValueOn if rule.get("enabled", True) else NSControlStateValueOff
            )
            
            # Load conditions
            for cond in rule.get("conditions", []):
                self.addCondition_(None)
                # TODO: Set condition values
            
            # Load actions
            for action in rule.get("actions", []):
                self.addAction_(None)
                # TODO: Set action values
        
        @python_method
        def _refresh_condition_layout(self):
            """Refresh the layout of condition rows."""
            for i, row in enumerate(self._condition_rows):
                row.setFrame_(NSMakeRect(0, (len(self._condition_rows) - 1 - i) * 40, 600, 36))
        
        @python_method
        def _refresh_action_layout(self):
            """Refresh the layout of action rows."""
            for i, row in enumerate(self._action_rows):
                row.setFrame_(NSMakeRect(0, (len(self._action_rows) - 1 - i) * 40, 600, 36))
        
        def addCondition_(self, sender):
            """Add a new condition row."""
            row = ConditionRowView.alloc_init_with_callback(
                on_change=self._on_condition_change,
                on_delete=self._on_condition_delete
            )
            self._condition_rows.append(row)
            self.conditions_container.addSubview_(row)
            self._refresh_condition_layout()
        
        def addAction_(self, sender):
            """Add a new action row."""
            row = ActionRowView.alloc_init_with_callback(
                on_change=self._on_action_change,
                on_delete=self._on_action_delete
            )
            self._action_rows.append(row)
            self.actions_container.addSubview_(row)
            self._refresh_action_layout()
        
        @python_method
        def _on_condition_change(self, row):
            """Handle condition change."""
            pass
        
        @python_method
        def _on_condition_delete(self, row):
            """Handle condition deletion."""
            if row in self._condition_rows:
                self._condition_rows.remove(row)
                row.removeFromSuperview()
                self._refresh_condition_layout()
        
        @python_method
        def _on_action_change(self, row):
            """Handle action change."""
            pass
        
        @python_method
        def _on_action_delete(self, row):
            """Handle action deletion."""
            if row in self._action_rows:
                self._action_rows.remove(row)
                row.removeFromSuperview()
                self._refresh_action_layout()
        
        def cancelClicked_(self, sender):
            """Handle cancel button click."""
            self.window.close()
        
        def saveClicked_(self, sender):
            """Handle save button click."""
            # Validate
            name = str(self.name_field.stringValue()).strip()
            if not name:
                self._show_alert("Error", "Please enter a rule name.")
                return
            
            if not self._condition_rows:
                self._show_alert("Error", "Please add at least one condition.")
                return
            
            if not self._action_rows:
                self._show_alert("Error", "Please add at least one action.")
                return
            
            # Build rule data
            match_modes = ["all", "any", "none"]
            
            rule_data = {
                "name": name,
                "description": str(self.description_field.stringValue()) or None,
                "match_mode": match_modes[self.match_popup.indexOfSelectedItem()],
                "continue_processing": self.continue_checkbox.state() == NSControlStateValueOn,
                "enabled": self.enabled_checkbox.state() == NSControlStateValueOn,
                "conditions": [row.get_condition_data() for row in self._condition_rows],
                "actions": [row.get_action_data() for row in self._action_rows],
            }
            
            # Call save callback
            if self._on_save:
                self._on_save(rule_data)
            
            self.window.close()
        
        @python_method
        def _show_alert(self, title: str, message: str):
            """Show an alert dialog."""
            alert = NSAlert.alloc().init()
            alert.setMessageText_(title)
            alert.setInformativeText_(message)
            alert.setAlertStyle_(NSAlertStyleWarning)
            alert.runModal()
        
        @python_method
        def show(self):
            """Show the window."""
            self.window.makeKeyAndOrderFront_(None)
            NSApp.activateIgnoringOtherApps_(True)


def show_rule_editor(on_save: Optional[Callable] = None, 
                     existing_rule: Optional[Dict] = None):
    """
    Show the rule editor window.
    
    Args:
        on_save: Callback function that receives the rule data when saved.
        existing_rule: Existing rule data to edit (optional).
    """
    if not HAS_APPKIT:
        print("AppKit not available - cannot show rule editor")
        return None
    
    controller = RuleEditorWindowController.alloc_init_with_callback(
        on_save=on_save,
        existing_rule=existing_rule
    )
    controller.show()
    return controller


# Test standalone
if __name__ == "__main__":
    if HAS_APPKIT:
        def on_rule_saved(rule_data):
            print("Rule saved:")
            import json
            print(json.dumps(rule_data, indent=2))
        
        app = NSApplication.sharedApplication()
        show_rule_editor(on_save=on_rule_saved)
        app.run()
    else:
        print("This module requires macOS with PyObjC installed.")
