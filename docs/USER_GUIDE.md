# SortMeOut User Guide

Welcome to SortMeOut - your intelligent file automation tool for macOS.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Installation](#installation)
3. [Basic Concepts](#basic-concepts)
4. [Creating Rules](#creating-rules)
5. [Conditions Reference](#conditions-reference)
6. [Actions Reference](#actions-reference)
7. [Menu Bar App](#menu-bar-app)
8. [Configuration](#configuration)
9. [Troubleshooting](#troubleshooting)

---

## Getting Started

SortMeOut watches folders you specify and automatically organizes files based on rules you create.

### How it works:

```
📁 Downloads/
    └── new-file.pdf arrives
           │
           ▼
    ┌──────────────┐
    │  Rule Check  │  ← Does file match any conditions?
    └──────────────┘
           │
           ▼
    ┌──────────────┐
    │   Actions    │  ← Move, rename, tag, etc.
    └──────────────┘
           │
           ▼
📁 Documents/PDFs/new-file.pdf
```

---

## Installation

### Method 1: DMG (Recommended)

1. Download `SortMeOut.dmg` from [sortmeout.saidborna.com](https://sortmeout.saidborna.com)
2. Open the DMG file
3. Drag SortMeOut to Applications
4. Launch from Applications folder
5. Grant necessary permissions when prompted

### Required Permissions

SortMeOut needs the following permissions to work:

| Permission | Why needed |
|------------|------------|
| **Full Disk Access** | To watch and move files in all folders |
| **Notifications** | To show alerts when actions are performed |
| **Accessibility** | For some advanced automation features |

To grant permissions:
1. Open **System Settings** → **Privacy & Security**
2. Find each permission category
3. Enable SortMeOut

---

## Basic Concepts

### Watched Folders

Folders that SortMeOut monitors for new or changed files.

**Common watched folders:**
- `~/Downloads` - Automatically organize downloaded files
- `~/Desktop` - Keep desktop clean
- `~/Documents` - Sort documents into subfolders

### Rules

A rule consists of:
1. **Name** - Description of what the rule does
2. **Conditions** - When the rule should trigger
3. **Actions** - What to do when conditions match
4. **Priority** - Order rules are checked (lower = first)

### Conditions

Criteria that files must match for the rule to trigger.

**Examples:**
- File extension is `.pdf`
- File name contains "invoice"
- File size > 10 MB
- Created within last 7 days

### Actions

What happens when a file matches all conditions.

**Examples:**
- Move to specific folder
- Rename with pattern
- Add macOS tag
- Archive/compress

---

## Creating Rules

### Step 1: Add a Watched Folder

1. Click the menu bar icon
2. Select **Preferences** → **Folders**
3. Click **+** to add a folder
4. Choose the folder to watch

### Step 2: Create a Rule

1. Go to **Preferences** → **Rules**
2. Click **+** to create new rule
3. Name your rule descriptively
4. Add conditions and actions

### Example Rules

#### Organize PDFs

```
Name: Move PDFs to Documents
Folder: ~/Downloads

Conditions:
  - Extension is "pdf"

Actions:
  - Move to ~/Documents/PDFs/
```

#### Clean Old Downloads

```
Name: Trash old downloads
Folder: ~/Downloads

Conditions:
  - Date added is more than 30 days ago
  - NOT in subfolder

Actions:
  - Move to Trash
```

#### Sort Screenshots

```
Name: Organize screenshots
Folder: ~/Desktop

Conditions:
  - Name starts with "Screenshot"
  - Extension is "png"

Actions:
  - Move to ~/Pictures/Screenshots/
  - Rename to "{date} - Screenshot.png"
```

---

## Conditions Reference

| Condition | Options | Example |
|-----------|---------|---------|
| **Name contains** | Text | "invoice" |
| **Name starts with** | Text | "IMG_" |
| **Name ends with** | Text | "_backup" |
| **Name matches** | Regex | `\d{4}-\d{2}-\d{2}` |
| **Extension is** | Extension | "pdf", "jpg" |
| **Kind is** | Type | Image, Document, Video |
| **Size** | >, <, between | > 10 MB |
| **Date created** | Timeframe | Within 7 days |
| **Date modified** | Timeframe | More than 30 days ago |
| **Tag is** | macOS tag | Red, Work |
| **Tag is not** | macOS tag | Processed |

### Combining Conditions

- **ALL** - All conditions must match (AND)
- **ANY** - At least one must match (OR)
- **NONE** - None can match (NOT)

---

## Actions Reference

| Action | Parameters | Example |
|--------|------------|---------|
| **Move to** | Destination folder | ~/Documents/Work/ |
| **Copy to** | Destination folder | ~/Backup/ |
| **Rename** | Pattern | "{date} - {name}" |
| **Add tag** | Tag name/color | "Processed" / Blue |
| **Remove tag** | Tag name | "Inbox" |
| **Archive** | Format (zip/tar) | Create zip |
| **Delete** | - | Move to Trash |
| **Open with** | Application | Preview.app |
| **Run script** | Shell command | `echo "done"` |

### Rename Patterns

| Pattern | Replaced with |
|---------|---------------|
| `{name}` | Original filename (without extension) |
| `{ext}` | File extension |
| `{date}` | Today's date (YYYY-MM-DD) |
| `{time}` | Current time (HH-MM-SS) |
| `{created}` | File creation date |
| `{modified}` | File modification date |
| `{counter}` | Auto-incrementing number |
| `{parent}` | Parent folder name |

---

## Menu Bar App

The menu bar icon shows SortMeOut status and provides quick access.

### Icon States

| Icon | Meaning |
|------|---------|
| 📁 (normal) | Running normally |
| 📁 (pulsing) | Processing files |
| ⚠️ | Error or warning |
| ⏸️ | Paused |

### Menu Options

- **Pause/Resume** - Temporarily stop processing
- **Process Now** - Force check all watched folders
- **Recent Activity** - Show recent file operations
- **Preferences** - Open settings
- **Quit** - Stop SortMeOut

---

## Configuration

### Config File Location

```
~/.config/sortmeout/config.json
```

### Settings

| Setting | Description | Default |
|---------|-------------|---------|
| `start_at_login` | Auto-start on boot | true |
| `check_interval` | Seconds between checks | 5 |
| `show_notifications` | Show alerts | true |
| `log_level` | Debug verbosity | "info" |
| `preview_mode` | Don't actually move files | false |

---

## Troubleshooting

### Files not being processed

1. Check SortMeOut is running (menu bar icon)
2. Verify folder is in watched list
3. Check rule conditions match the file
4. Ensure Full Disk Access is granted

### Permission errors

1. Open **System Settings** → **Privacy & Security**
2. Grant **Full Disk Access** to SortMeOut
3. Restart SortMeOut

### Rule not triggering

1. Check conditions are correct
2. Verify file actually matches (check name, extension, etc.)
3. Look at logs: `~/.config/sortmeout/sortmeout.log`

### High CPU usage

1. Reduce number of watched folders
2. Increase `check_interval` in settings
3. Exclude large folders with many files

---

## Getting Help

- **Documentation**: [sortmeout.saidborna.com/docs](https://sortmeout.saidborna.com)
- **Email**: support@saidborna.com

---

*Version 1.0 - Last updated February 2026*
