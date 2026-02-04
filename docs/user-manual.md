# SortMeOut User Manual

**Version 1.0.0**

A powerful, open-source file automation tool for macOS.

---

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Understanding Rules](#understanding-rules)
5. [Conditions Reference](#conditions-reference)
6. [Actions Reference](#actions-reference)
7. [Using the GUI](#using-the-gui)
8. [Using the CLI](#using-the-cli)
9. [Trash Management](#trash-management)
10. [App Sweep](#app-sweep)
11. [Advanced Features](#advanced-features)
12. [Troubleshooting](#troubleshooting)

---

## Introduction

SortMeOut is an open-source file automation tool designed to help you automatically organize, rename, move, and manage files on your Mac. Inspired by Noodlesoft Hazel, SortMeOut monitors folders you specify and automatically applies rules to incoming files.

### Key Features

- **Automated File Organization**: Set rules once and let SortMeOut do the work
- **Flexible Conditions**: Match files by name, extension, size, date, tags, and more
- **Powerful Actions**: Move, copy, rename, archive, tag, or delete files automatically
- **Trash Management**: Smart trash cleanup with age-based emptying
- **App Sweep**: Clean up application remnants when uninstalling apps
- **macOS Integration**: Native support for Finder tags, Spotlight, and more
- **Preview Mode**: Test rules without making changes
- **Menu Bar App**: Unobtrusive system tray application
- **Command Line Interface**: Full control from the terminal

---

## Installation

### Prerequisites

- macOS 11.0 (Big Sur) or later
- Python 3.9 or later

### Install via pip

```bash
pip install sortmeout
```

### Install from source

```bash
git clone https://github.com/yourusername/sortmeout.git
cd sortmeout
pip install -e .
```

### Verify Installation

```bash
sortmeout --version
```

---

## Quick Start

### 1. Add a Folder to Watch

```bash
sortmeout folder add ~/Downloads
```

### 2. Create a Simple Rule

```bash
sortmeout rule add "Organize PDFs" \
    --condition "extension equals pdf" \
    --action "move ~/Documents/PDFs"
```

### 3. Start SortMeOut

```bash
sortmeout start
```

That's it! PDF files appearing in your Downloads folder will now be automatically moved to Documents/PDFs.

---

## Understanding Rules

Rules are the heart of SortMeOut. Each rule consists of:

1. **Name**: A descriptive name for the rule
2. **Conditions**: Criteria that files must match
3. **Actions**: What to do when a file matches
4. **Match Mode**: How to combine multiple conditions

### Match Modes

| Mode | Description |
|------|-------------|
| ALL | File must match ALL conditions |
| ANY | File must match at least ONE condition |
| NONE | File must match NONE of the conditions |

### Rule Priority

Rules are processed in priority order (highest first). When a rule matches:

- By default, subsequent rules are also evaluated
- Set `stop_processing=True` to stop after a match

### Example Rule Structure

```yaml
name: "Archive Old Downloads"
match_mode: all
priority: 10
enabled: true
conditions:
  - attribute: date_added
    operator: older_than
    value: "30 days"
  - attribute: extension
    operator: in_list
    value: ["zip", "dmg", "pkg"]
actions:
  - action_type: archive
    params:
      format: zip
  - action_type: move
    params:
      destination: ~/Archives
```

---

## Conditions Reference

### String Conditions

| Operator | Description | Example |
|----------|-------------|---------|
| equals | Exact match | `name equals "report"` |
| not_equals | Not equal | `extension not_equals "tmp"` |
| contains | Contains substring | `name contains "invoice"` |
| not_contains | Doesn't contain | `name not_contains "draft"` |
| starts_with | Begins with | `name starts_with "IMG_"` |
| ends_with | Ends with | `name ends_with "_final"` |
| matches | Regex pattern | `name matches "^[0-9]{4}-[0-9]{2}"` |

### Numeric Conditions

| Operator | Description | Example |
|----------|-------------|---------|
| greater_than | Greater than | `size greater_than "10 MB"` |
| less_than | Less than | `size less_than "100 KB"` |
| between | In range | `size between "1 MB, 100 MB"` |

### Date Conditions

| Operator | Description | Example |
|----------|-------------|---------|
| older_than | Older than duration | `date_modified older_than "7 days"` |
| newer_than | Newer than duration | `date_created newer_than "1 hour"` |
| before | Before date | `date_added before "2024-01-01"` |
| after | After date | `date_modified after "2024-06-01"` |

### List Conditions

| Operator | Description | Example |
|----------|-------------|---------|
| in_list | Value in list | `extension in_list ["jpg", "png", "gif"]` |
| not_in_list | Value not in list | `extension not_in_list ["exe", "bat"]` |

### Existence Conditions

| Operator | Description | Example |
|----------|-------------|---------|
| exists | Attribute exists | `tags exists` |
| not_exists | Attribute doesn't exist | `comment not_exists` |
| is_empty | Value is empty | `tags is_empty` |
| is_not_empty | Value is not empty | `name is_not_empty` |

### Supported Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| name | String | File name without extension |
| full_name | String | Complete filename |
| extension | String | File extension |
| path | String | Full file path |
| parent_folder | String | Parent folder name |
| size | Number | File size in bytes |
| date_created | Date | Creation date |
| date_modified | Date | Last modification date |
| date_added | Date | Date added to folder |
| kind | String | File kind (image, document, etc.) |
| tags | List | Finder tags |
| comment | String | Finder comment |
| content | String | File content (text files) |

---

## Actions Reference

### File Operations

#### Move

Move file to a destination folder.

```yaml
action_type: move
params:
  destination: ~/Documents/Sorted
  if_exists: rename  # rename, overwrite, skip
```

#### Copy

Copy file to a destination folder.

```yaml
action_type: copy
params:
  destination: ~/Backup
```

#### Rename

Rename the file.

```yaml
action_type: rename
params:
  new_name: "{date}_{name}.{extension}"
```

#### Delete

Permanently delete the file.

```yaml
action_type: delete
params:
  force: true
```

#### Trash

Move file to Trash.

```yaml
action_type: trash
```

### Archive Operations

#### Archive

Create an archive of the file.

```yaml
action_type: archive
params:
  format: zip  # zip, tar, tar.gz
  delete_original: true
```

#### Unarchive

Extract archive contents.

```yaml
action_type: unarchive
params:
  destination: ~/Extracted
```

### Tag Operations

#### Add Tags

Add Finder tags to the file.

```yaml
action_type: add_tags
params:
  tags: ["Important", "Work"]
```

#### Remove Tags

Remove Finder tags from the file.

```yaml
action_type: remove_tags
params:
  tags: ["Temporary"]
```

#### Set Tags

Replace all tags with new ones.

```yaml
action_type: set_tags
params:
  tags: ["Archived"]
```

### Other Actions

#### Notify

Show a system notification.

```yaml
action_type: notify
params:
  title: "File Processed"
  message: "Moved {full_name} to Documents"
```

#### Run Shell Script

Execute a shell command.

```yaml
action_type: shell
params:
  command: "echo 'Processed: {path}' >> ~/log.txt"
```

#### Run AppleScript

Execute AppleScript code.

```yaml
action_type: applescript
params:
  script: |
    tell application "Finder"
      set comment of POSIX file "{path}" to "Processed by SortMeOut"
    end tell
```

### Variable Expansion

Actions support variable expansion using `{variable}` syntax:

| Variable | Description |
|----------|-------------|
| {name} | File name without extension |
| {extension} | File extension |
| {full_name} | Complete filename |
| {path} | Full file path |
| {parent_folder} | Parent folder name |
| {date} | Current date (YYYY-MM-DD) |
| {time} | Current time (HH-MM-SS) |
| {year} | Current year |
| {month} | Current month |
| {day} | Current day |

---

## Using the GUI

SortMeOut includes a menu bar application for easy access.

### Starting the GUI

```bash
sortmeout-gui
```

Or from the CLI:

```bash
sortmeout gui
```

### Menu Bar Options

- **Start/Stop**: Toggle file monitoring
- **Preview Mode**: Enable/disable preview mode
- **Folders**: View and manage watched folders
- **Trash**: Access trash management options
- **Preferences**: Open settings

### Preview Mode

When preview mode is enabled:

- Rules are matched but actions are not executed
- Notifications show what would happen
- Useful for testing new rules

---

## Using the CLI

### Folder Commands

```bash
# Add a folder to watch
sortmeout folder add ~/Downloads

# Remove a folder
sortmeout folder remove ~/Downloads

# List watched folders
sortmeout folder list

# Process a folder manually
sortmeout folder process ~/Downloads
```

### Rule Commands

```bash
# Add a rule
sortmeout rule add "Name" --condition "..." --action "..."

# List all rules
sortmeout rule list

# Show rule details
sortmeout rule show <rule-id>

# Enable/disable a rule
sortmeout rule enable <rule-id>
sortmeout rule disable <rule-id>

# Export rules
sortmeout rule export rules.yaml

# Import rules
sortmeout rule import rules.yaml
```

### Control Commands

```bash
# Start monitoring
sortmeout start

# Stop monitoring
sortmeout stop

# Check status
sortmeout status

# Test a file against rules
sortmeout test ~/Downloads/file.pdf
```

### Configuration

```bash
# Show configuration
sortmeout config show

# Export configuration
sortmeout config export config.yaml

# Import configuration
sortmeout config import config.yaml

# Reset to defaults
sortmeout config reset
```

---

## Trash Management

SortMeOut provides smart trash management features.

### Automatic Trash Emptying

Configure automatic trash emptying based on file age:

```bash
sortmeout config set trash.auto_empty_after "7 days"
```

### Manual Trash Management

```bash
# View trash status
sortmeout trash status

# Empty trash (files older than 30 days)
sortmeout trash empty --age "30 days"

# Force empty all trash
sortmeout trash empty --force
```

---

## App Sweep

When you delete an application, App Sweep helps clean up leftover files.

### How It Works

1. Detects when an app is moved to Trash
2. Finds associated support files:
   - Application Support files
   - Preferences
   - Caches
   - Containers
   - Logs
3. Offers to remove them

### Using App Sweep

```bash
# Find app-related files
sortmeout trash clean "App Name.app"

# Interactive cleanup
sortmeout trash clean --interactive
```

---

## Advanced Features

### Condition Groups

Create complex nested conditions:

```yaml
conditions:
  - type: group
    match_mode: any
    conditions:
      - attribute: extension
        operator: equals
        value: "jpg"
      - attribute: extension
        operator: equals
        value: "png"
```

### Rule Chaining

Process files through multiple rules:

```yaml
# Rule 1: Tag images
name: "Tag Images"
conditions:
  - attribute: extension
    operator: in_list
    value: ["jpg", "png", "gif"]
actions:
  - action_type: add_tags
    params:
      tags: ["Image"]
stop_processing: false  # Continue to next rule

# Rule 2: Move tagged images
name: "Move Images"
conditions:
  - attribute: tags
    operator: contains
    value: "Image"
actions:
  - action_type: move
    params:
      destination: ~/Pictures
```

### Scheduled Processing

Set up periodic folder processing:

```bash
# Process folder every hour
sortmeout schedule add ~/Downloads --interval "1 hour"
```

### Custom Scripts

Run custom shell scripts as actions:

```yaml
action_type: shell
params:
  command: |
    #!/bin/bash
    FILE="{path}"
    # Custom processing here
    echo "Processed: $FILE"
```

---

## Troubleshooting

### Common Issues

#### Rules Not Triggering

1. Check if SortMeOut is running: `sortmeout status`
2. Verify the folder is being watched: `sortmeout folder list`
3. Test the rule: `sortmeout test /path/to/file`
4. Enable verbose logging: `sortmeout start --verbose`

#### Permission Errors

Grant Full Disk Access to SortMeOut:

1. Open System Preferences > Security & Privacy > Privacy
2. Select "Full Disk Access"
3. Add SortMeOut or Terminal to the list

#### Files Not Moving

1. Check destination folder exists
2. Verify write permissions
3. Check for file conflicts
4. Review action parameters

### Logs

View logs for debugging:

```bash
# Show recent logs
sortmeout logs

# Follow logs in real-time
sortmeout logs --follow

# Log location
cat ~/Library/Logs/SortMeOut/sortmeout.log
```

### Getting Help

```bash
# General help
sortmeout --help

# Command-specific help
sortmeout rule --help
sortmeout rule add --help
```

---

## Support

- **Documentation**: <https://sortmeout.readthedocs.io>
- **Issues**: <https://github.com/yourusername/sortmeout/issues>
- **Discussions**: <https://github.com/yourusername/sortmeout/discussions>

---

*SortMeOut is open-source software licensed under the MIT License.*
