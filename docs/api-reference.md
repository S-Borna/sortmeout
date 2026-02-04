# SortMeOut API Reference

Technical reference for developers using SortMeOut as a library.

---

## Table of Contents

1. [Core Classes](#core-classes)
2. [Conditions](#conditions)
3. [Actions](#actions)
4. [Watchers](#watchers)
5. [Configuration](#configuration)
6. [macOS Integration](#macos-integration)

---

## Core Classes

### SortMeOut

The main application class.

```python
from sortmeout import SortMeOut

app = SortMeOut()
```

#### Methods

| Method | Description |
|--------|-------------|
| `start()` | Start file monitoring |
| `stop()` | Stop file monitoring |
| `add_folder(path, **options)` | Add a folder to watch |
| `remove_folder(path)` | Remove a watched folder |
| `add_rule(rule)` | Add a rule |
| `remove_rule(rule_id)` | Remove a rule |
| `process_file(path)` | Manually process a file |
| `get_status()` | Get current status |
| `export_config(path)` | Export configuration |
| `import_config(path)` | Import configuration |

#### Example

```python
from sortmeout import SortMeOut
from sortmeout.core import Rule, Condition, Action

app = SortMeOut()

# Add a watched folder
app.add_folder("~/Downloads", recursive=True)

# Create and add a rule
rule = Rule(
    name="Organize PDFs",
    conditions=[Condition("extension", "equals", "pdf")],
    actions=[Action("move", destination="~/Documents/PDFs")]
)
app.add_rule(rule)

# Start monitoring
app.start()
```

---

### Rule

Represents a file processing rule.

```python
from sortmeout.core import Rule, MatchMode

rule = Rule(
    name="My Rule",
    match_mode=MatchMode.ALL,
    priority=10,
    enabled=True,
    stop_processing=False,
)
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | str | required | Rule name |
| `match_mode` | MatchMode | ALL | How to combine conditions |
| `conditions` | list | [] | List of conditions |
| `actions` | list | [] | List of actions |
| `priority` | int | 0 | Processing priority |
| `enabled` | bool | True | Is rule active |
| `stop_processing` | bool | False | Stop after match |

#### Methods

| Method | Description |
|--------|-------------|
| `add_condition(condition)` | Add a condition |
| `remove_condition(id)` | Remove a condition |
| `add_action(action)` | Add an action |
| `remove_action(id)` | Remove an action |
| `matches(file_info)` | Check if file matches |
| `to_dict()` | Serialize to dictionary |
| `from_dict(data)` | Deserialize from dictionary |
| `duplicate()` | Create a copy |
| `validate()` | Validate rule configuration |

#### MatchMode Enum

```python
from sortmeout.core import MatchMode

MatchMode.ALL   # All conditions must match
MatchMode.ANY   # At least one condition must match
MatchMode.NONE  # No conditions must match
```

---

### RuleEngine

Processes files against rules.

```python
from sortmeout.core import RuleEngine

engine = RuleEngine()
```

#### Methods

| Method | Description |
|--------|-------------|
| `add_rule(rule)` | Add a rule |
| `remove_rule(rule_id)` | Remove a rule |
| `get_rule(rule_id)` | Get a rule by ID |
| `process_file(path, preview=False)` | Process a file |
| `find_matching_rules(file_info)` | Find rules that match |
| `preview_rule(rule, path)` | Preview rule execution |
| `export_rules(path)` | Export rules to file |
| `import_rules(path)` | Import rules from file |

#### Example

```python
from sortmeout.core import RuleEngine, Rule, Condition, Action

engine = RuleEngine()

# Add rules
engine.add_rule(Rule(
    name="PDF Handler",
    conditions=[Condition("extension", "equals", "pdf")],
    actions=[Action("move", destination="~/Documents")]
))

# Process a file
result = engine.process_file("~/Downloads/report.pdf")

if result.success:
    print(f"Processed: {result.rules_applied} rules applied")
else:
    print(f"Error: {result.error}")
```

---

## Conditions

### Condition

Represents a single condition.

```python
from sortmeout.core import Condition

condition = Condition(
    attribute="extension",
    operator="equals",
    value="pdf",
    negate=False,
)
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `attribute` | str | required | File attribute to check |
| `operator` | str | required | Comparison operator |
| `value` | any | required | Value to compare against |
| `negate` | bool | False | Invert the result |

#### Methods

| Method | Description |
|--------|-------------|
| `evaluate(file_info)` | Evaluate against file |
| `to_dict()` | Serialize to dictionary |
| `from_dict(data)` | Deserialize |

#### Supported Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `name` | str | Filename without extension |
| `full_name` | str | Complete filename |
| `extension` | str | File extension |
| `path` | str | Full file path |
| `parent_folder` | str | Parent folder name |
| `size` | int | Size in bytes |
| `date_created` | datetime | Creation date |
| `date_modified` | datetime | Modification date |
| `date_added` | datetime | Date added |
| `kind` | str | File kind |
| `tags` | list | Finder tags |
| `comment` | str | Finder comment |
| `content` | str | File content |

#### Supported Operators

**String Operators**

```python
Condition("name", "equals", "report")
Condition("name", "not_equals", "draft")
Condition("name", "contains", "invoice")
Condition("name", "not_contains", "temp")
Condition("name", "starts_with", "IMG_")
Condition("name", "ends_with", "_final")
Condition("name", "matches", r"^\d{4}-\d{2}-\d{2}")
```

**Numeric Operators**

```python
Condition("size", "greater_than", "10 MB")
Condition("size", "less_than", "100 KB")
Condition("size", "between", "1 MB, 10 MB")
```

**Date Operators**

```python
Condition("date_modified", "older_than", "7 days")
Condition("date_created", "newer_than", "1 hour")
Condition("date_added", "before", "2024-01-01")
Condition("date_modified", "after", "2024-06-01")
```

**List Operators**

```python
Condition("extension", "in_list", ["jpg", "png", "gif"])
Condition("extension", "not_in_list", ["exe", "bat"])
```

**Existence Operators**

```python
Condition("tags", "exists")
Condition("comment", "not_exists")
Condition("tags", "is_empty")
Condition("name", "is_not_empty")
```

---

### ConditionGroup

Groups multiple conditions with a match mode.

```python
from sortmeout.core import ConditionGroup

group = ConditionGroup(
    match_mode="any",
    conditions=[
        Condition("extension", "equals", "jpg"),
        Condition("extension", "equals", "png"),
    ]
)
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `match_mode` | str | "all" | How to combine conditions |
| `conditions` | list | [] | List of conditions |

---

### Convenience Functions

```python
from sortmeout.core.condition import (
    name_equals,
    name_contains,
    name_starts_with,
    name_ends_with,
    name_matches,
    extension_equals,
    extension_in_list,
    size_greater_than,
    size_less_than,
    older_than,
    newer_than,
    has_tag,
)

# Examples
condition = extension_equals("pdf")
condition = size_greater_than("10 MB")
condition = older_than("30 days")
condition = has_tag("Work")
```

---

## Actions

### Action

Represents an action to perform.

```python
from sortmeout.core import Action, ActionType

action = Action(
    action_type="move",
    destination="~/Documents",
    if_exists="rename",
)
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `action_type` | str/ActionType | required | Type of action |
| `enabled` | bool | True | Is action active |
| `stop_on_error` | bool | True | Stop on failure |
| `**params` | any | - | Action-specific parameters |

#### Methods

| Method | Description |
|--------|-------------|
| `execute(path, file_info, preview=False)` | Execute the action |
| `to_dict()` | Serialize to dictionary |
| `from_dict(data)` | Deserialize |
| `duplicate()` | Create a copy |

#### ActionType Enum

```python
from sortmeout.core import ActionType

ActionType.MOVE
ActionType.COPY
ActionType.RENAME
ActionType.DELETE
ActionType.TRASH
ActionType.ARCHIVE
ActionType.UNARCHIVE
ActionType.ADD_TAGS
ActionType.REMOVE_TAGS
ActionType.SET_TAGS
ActionType.SET_COMMENT
ActionType.NOTIFY
ActionType.SHELL
ActionType.APPLESCRIPT
ActionType.OPEN
ActionType.REVEAL
```

---

### Action Types Reference

#### Move

```python
Action(
    "move",
    destination="~/Documents/Sorted",
    if_exists="rename",  # rename, overwrite, skip
)
```

#### Copy

```python
Action(
    "copy",
    destination="~/Backup",
    if_exists="skip",
)
```

#### Rename

```python
Action(
    "rename",
    new_name="{date}_{name}.{extension}",
    if_exists="rename",
)
```

#### Delete

```python
Action(
    "delete",
    force=True,  # Skip confirmation
)
```

#### Trash

```python
Action("trash")
```

#### Archive

```python
Action(
    "archive",
    format="zip",  # zip, tar, tar.gz
    delete_original=True,
)
```

#### Tags

```python
Action("add_tags", tags=["Work", "Important"])
Action("remove_tags", tags=["Temporary"])
Action("set_tags", tags=["Archived"])
```

#### Notify

```python
Action(
    "notify",
    title="File Processed",
    message="Moved {full_name} to Documents",
)
```

#### Shell

```python
Action(
    "shell",
    command="echo 'Processed: {path}' >> ~/log.txt",
)
```

#### AppleScript

```python
Action(
    "applescript",
    script='''
    tell application "Finder"
        set comment of POSIX file "{path}" to "Processed"
    end tell
    '''
)
```

---

### ActionResult

Result of action execution.

```python
from sortmeout.core import ActionResult

result = ActionResult(
    success=True,
    action_type=ActionType.MOVE,
    source_path="/source/file.txt",
    destination_path="/dest/file.txt",
    message="File moved successfully",
)
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `success` | bool | Was action successful |
| `action_type` | ActionType | Type of action |
| `source_path` | str | Original file path |
| `destination_path` | str | New path (if applicable) |
| `message` | str | Status message |
| `error` | str | Error message (if failed) |
| `metadata` | dict | Additional info |

---

### Convenience Functions

```python
from sortmeout.core.action import (
    move_to,
    copy_to,
    rename,
    delete,
    trash,
    archive,
    add_tags,
    remove_tags,
    notify,
)

# Examples
action = move_to("~/Documents")
action = rename("{date}_{name}.{extension}")
action = add_tags("Work", "Important")
action = notify("Done", "File processed")
```

---

## Watchers

### FolderWatcher

Monitors a folder for changes.

```python
from sortmeout.core import FolderWatcher

def on_file_changed(path):
    print(f"File changed: {path}")

watcher = FolderWatcher(
    folder_path="~/Downloads",
    callback=on_file_changed,
    recursive=True,
)
```

#### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `folder_path` | str | required | Path to watch |
| `callback` | callable | required | Function to call on events |
| `recursive` | bool | True | Watch subdirectories |
| `ignore_patterns` | list | [] | Patterns to ignore |
| `include_extensions` | list | None | Extensions to include |
| `exclude_extensions` | list | None | Extensions to exclude |
| `ignore_hidden` | bool | True | Ignore hidden files |

#### Methods

| Method | Description |
|--------|-------------|
| `start()` | Start watching |
| `stop()` | Stop watching |
| `should_process(path)` | Check if file should be processed |
| `get_stats()` | Get statistics |
| `to_dict()` | Serialize |
| `from_dict(data, callback)` | Deserialize |

---

### WatcherManager

Manages multiple watchers.

```python
from sortmeout.core import WatcherManager

manager = WatcherManager()
```

#### Methods

| Method | Description |
|--------|-------------|
| `add_watcher(path, callback, **options)` | Add a watcher |
| `remove_watcher(path)` | Remove a watcher |
| `get_watcher(path)` | Get a watcher |
| `start_all()` | Start all watchers |
| `stop_all()` | Stop all watchers |
| `list_watched_folders()` | List watched paths |

---

## Configuration

### ConfigManager

Manages application configuration.

```python
from sortmeout.config import ConfigManager

config = ConfigManager()
```

#### Methods

| Method | Description |
|--------|-------------|
| `get(key, default=None)` | Get a setting |
| `set(key, value)` | Set a setting |
| `save()` | Save configuration |
| `load()` | Load configuration |
| `export(path)` | Export to file |
| `import_config(path)` | Import from file |
| `reset()` | Reset to defaults |

#### Configuration Keys

```python
# General
config.get("auto_start")
config.get("preview_mode")
config.get("notification_sound")

# Trash
config.get("trash.auto_empty_after")
config.get("trash.app_sweep_enabled")

# Logging
config.get("logging.level")
config.get("logging.file")
```

---

## macOS Integration

### Tags

```python
from sortmeout.macos import tags

# Get tags
file_tags = tags.get_tags("/path/to/file")

# Set tags
tags.set_tags("/path/to/file", ["Work", "Important"])

# Add tags
tags.add_tags("/path/to/file", ["New Tag"])

# Remove tags
tags.remove_tags("/path/to/file", ["Old Tag"])

# Get Finder comment
comment = tags.get_comment("/path/to/file")

# Set Finder comment
tags.set_comment("/path/to/file", "My comment")
```

---

### Spotlight

```python
from sortmeout.macos import spotlight

# Search by query
results = spotlight.search_spotlight("kind:image date:today")

# Get file metadata
metadata = spotlight.get_metadata("/path/to/file")

# Find files by kind
images = spotlight.find_by_kind("image", scope="~/Pictures")

# Find by extension
pdfs = spotlight.find_by_extension("pdf", scope="~/Documents")

# Find by tag
work_files = spotlight.find_by_tag("Work")

# Find by content
results = spotlight.find_by_content("project proposal")
```

---

### Trash

```python
from sortmeout.macos import trash

# Get trash info
info = trash.get_trash_info()
print(f"Items: {info.item_count}, Size: {info.total_size}")

# List trash items
items = trash.list_trash_items()
for item in items:
    print(f"{item.original_name} - deleted {item.deletion_date}")

# Empty trash
trash.empty_trash(older_than="7 days")

# Force empty all
trash.empty_trash(force=True)

# Restore item
trash.restore_item(item.path)
```

---

### App Sweep

```python
from sortmeout.macos.trash import AppSweep

sweep = AppSweep()

# Find app support files
files = sweep.find_app_support_files("AppName")
for f in files:
    print(f"Found: {f.path} ({f.category})")

# Clean up
sweep.clean_app_support_files("AppName", interactive=True)
```

---

## Utilities

### File Info

```python
from sortmeout.utils import get_file_info

info = get_file_info("/path/to/file.txt")
print(info["name"])        # "file"
print(info["extension"])   # "txt"
print(info["size"])        # 1234
print(info["date_created"])
```

---

### Logging

```python
from sortmeout.utils import logger

logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
```

---

## Complete Example

```python
#!/usr/bin/env python3
"""
Complete SortMeOut automation script.
"""

from sortmeout import SortMeOut
from sortmeout.core import Rule, Condition, ConditionGroup, Action, MatchMode

def main():
    # Initialize
    app = SortMeOut()

    # Watch Downloads folder
    app.add_folder("~/Downloads", recursive=True)

    # Rule 1: Organize images
    app.add_rule(Rule(
        name="Organize Images",
        match_mode=MatchMode.ALL,
        conditions=[
            Condition("extension", "in_list", ["jpg", "png", "gif", "heic"])
        ],
        actions=[
            Action("move", destination="~/Pictures/Downloads"),
            Action("notify", title="Image Organized", message="{full_name}")
        ],
        priority=10,
    ))

    # Rule 2: Handle PDFs
    app.add_rule(Rule(
        name="Sort PDFs",
        conditions=[Condition("extension", "equals", "pdf")],
        actions=[
            Action("add_tags", tags=["Document"]),
            Action("move", destination="~/Documents/PDFs")
        ],
        priority=9,
    ))

    # Rule 3: Archive old downloads
    app.add_rule(Rule(
        name="Archive Old Files",
        match_mode=MatchMode.ALL,
        conditions=[
            Condition("date_added", "older_than", "30 days"),
            ConditionGroup(
                match_mode="any",
                conditions=[
                    Condition("extension", "equals", "zip"),
                    Condition("extension", "equals", "dmg"),
                ]
            )
        ],
        actions=[
            Action("trash")
        ],
        priority=5,
    ))

    # Start monitoring
    print("Starting SortMeOut...")
    app.start()

    # Keep running
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        app.stop()

if __name__ == "__main__":
    main()
```

---

*For more examples, see the [GitHub repository](https://github.com/yourusername/sortmeout).*
