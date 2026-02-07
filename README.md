# SortMeOut

**Intelligent file automation and AI desktop assistant for macOS.**

[![Version](https://img.shields.io/badge/version-1.0.1-6366F1.svg)](https://sortmeout.saidborna.com)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![macOS](https://img.shields.io/badge/platform-macOS-lightgrey.svg)](https://www.apple.com/macos/)
[![Tests](https://img.shields.io/badge/tests-207%20passing-brightgreen.svg)](#testing)
[![License](https://img.shields.io/badge/license-Proprietary-red.svg)](#license)

> Rule-based file automation + an AI-powered desktop assistant that can search, tag, compress, control system settings, and more — all from the menu bar.

**Website:** [sortmeout.saidborna.com](https://sortmeout.saidborna.com)
**Author:** Said Borna

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Core Modules](#core-modules)
  - [Rules Engine](#rules-engine)
  - [Conditions](#conditions)
  - [Actions](#actions)
  - [Folder Watcher](#folder-watcher)
  - [Scheduler](#scheduler)
  - [History & Undo](#history--undo)
  - [License System](#license-system)
- [AI Assistant](#ai-assistant)
  - [AI Architecture](#ai-architecture)
  - [31 System Commands](#31-system-commands)
  - [Chat Window](#chat-window)
- [macOS Integration](#macos-integration)
  - [Spotlight](#spotlight)
  - [Finder Tags](#finder-tags)
  - [Trash Management](#trash-management)
  - [System Commands](#system-commands)
- [GUI Layer](#gui-layer)
  - [Menu Bar App](#menu-bar-app)
  - [Rule Editor](#rule-editor)
  - [Settings Window](#settings-window)
  - [Chat Window UI](#chat-window-ui)
- [CLI](#cli)
- [Configuration](#configuration)
- [Templates](#templates)
- [Backend & Payments](#backend--payments)
- [Tech Stack](#tech-stack)
- [Testing](#testing)
- [Building & Distribution](#building--distribution)
- [Installation](#installation)

---

## Overview

SortMeOut is a macOS desktop application that automatically organizes files based on user-defined rules — similar to Noodlesoft Hazel, but with a built-in AI assistant powered by Claude that can do far more than just move files.

The app runs in the macOS menu bar, watches folders in real-time, and applies rules that match conditions (file name, type, size, date, content, tags, etc.) to actions (move, copy, rename, tag, archive, trash, open, run scripts, and more).

On top of the rule engine, the AI assistant acts as a full desktop companion — it can search files via Spotlight, manage Finder tags, compress/decompress archives, take screenshots, toggle dark mode, check battery/disk/WiFi status, control volume, send notifications, speak text aloud, and 20+ other system operations.

### Key Numbers

| Metric | Value |
|--------|-------|
| Python source files | 34 |
| Lines of code (app) | ~15,600 |
| Lines of code (tests) | ~2,400 |
| Test cases | 207 (all passing) |
| AI commands | 31 |
| Rule conditions | 17 attribute types |
| Rule actions | 22 action types |
| Schedule intervals | 10 options |
| Template rules | 10+ prebuilt |

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    macOS Menu Bar                        │
│                     (rumps)                              │
├────────────┬──────────────┬─────────────────────────────┤
│  GUI Layer │  CLI Layer   │  AI Assistant               │
│  (AppKit/  │  (click/     │  (Anthropic Claude API)     │
│   PyObjC)  │   rich)      │                             │
├────────────┴──────────────┴─────────────────────────────┤
│                    Core Engine                           │
│  ┌──────────┐ ┌────────┐ ┌─────────┐ ┌───────────────┐ │
│  │ Watcher  │ │ Engine │ │Scheduler│ │   History      │ │
│  │(watchdog)│ │(rules) │ │(cron)   │ │   (SQLite)    │ │
│  └──────────┘ └────────┘ └─────────┘ └───────────────┘ │
│  ┌──────────┐ ┌────────┐ ┌─────────┐ ┌───────────────┐ │
│  │  Rules   │ │Actions │ │Condition│ │  Templates    │ │
│  └──────────┘ └────────┘ └─────────┘ └───────────────┘ │
├─────────────────────────────────────────────────────────┤
│               macOS Integration Layer                    │
│  ┌──────────┐ ┌────────┐ ┌─────────┐ ┌───────────────┐ │
│  │Spotlight │ │  Tags  │ │  Trash  │ │    System     │ │
│  │(mdfind)  │ │(xattr) │ │(Finder) │ │  (osascript)  │ │
│  └──────────┘ └────────┘ └─────────┘ └───────────────┘ │
├─────────────────────────────────────────────────────────┤
│                  Config Layer                            │
│        ConfigManager (YAML/JSON) + Settings              │
├─────────────────────────────────────────────────────────┤
│              License Authority (Singleton)               │
│       Trial (7 days) → Pro ($9.99/mo via Stripe)        │
└─────────────────────────────────────────────────────────┘
```

### Data Flow

1. **File event** → `watchdog` detects a change in a watched folder
2. **Event handler** → `FileEventHandler` debounces and filters events
3. **Rule engine** → `RuleEngine.process_file()` evaluates all rules in order
4. **Condition evaluation** → Each rule's conditions are checked (AND/OR/NOT logic)
5. **Action execution** → Matching rules execute their actions
6. **History recording** → Every action is recorded to SQLite via `HistoryManager`
7. **Notification** → User is notified via macOS notifications (batched)

---

## Project Structure

```
sortmeout/
├── sortmeout/                  # Main package
│   ├── __init__.py             # Package root, exports SortMeOut, Rule, Condition, Action
│   ├── app.py                  # Main application class (728 lines)
│   ├── cli.py                  # Full CLI with click + rich (1,122 lines)
│   │
│   ├── core/                   # Core rule engine
│   │   ├── action.py           # 22 action types (1,241 lines)
│   │   ├── condition.py        # 17 condition attributes, operators (672 lines)
│   │   ├── engine.py           # Rule processing engine (615 lines)
│   │   ├── history.py          # SQLite history & undo (713 lines)
│   │   ├── license.py          # License authority singleton (700 lines)
│   │   ├── rule.py             # Rule dataclass & serialization (324 lines)
│   │   ├── scheduler.py        # Scheduled rules (cron-like) (309 lines)
│   │   ├── templates.py        # Prebuilt rule templates (317 lines)
│   │   └── watcher.py          # FSEvents folder watcher (620 lines)
│   │
│   ├── ai/                     # AI assistant
│   │   ├── __init__.py
│   │   └── assistant.py        # Claude-powered assistant (1,471 lines)
│   │
│   ├── gui/                    # Native macOS GUI
│   │   ├── app.py              # Menu bar app (rumps) (822 lines)
│   │   ├── chat_window.py      # AI chat window (AppKit) (1,165 lines)
│   │   ├── rule_editor.py      # Visual rule editor (AppKit) (854 lines)
│   │   ├── settings_window.py  # Preferences window (AppKit) (495 lines)
│   │   └── main_window.py      # Entry point shim
│   │
│   ├── macos/                  # macOS-specific integrations
│   │   ├── spotlight.py        # Spotlight search (mdfind/mdls) (345 lines)
│   │   ├── tags.py             # Finder tags CRUD (xattr) (318 lines)
│   │   ├── trash.py            # Trash management (456 lines)
│   │   └── system.py           # System commands (639 lines)
│   │
│   ├── config/                 # Configuration
│   │   ├── manager.py          # YAML/JSON config (322 lines)
│   │   └── settings.py         # Settings dataclasses (202 lines)
│   │
│   └── utils/                  # Utilities
│       ├── file_info.py        # File metadata extraction (363 lines)
│       └── logger.py           # Logging setup
│
├── tests/                      # Test suite (207 tests)
│   ├── test_action.py          # Action tests
│   ├── test_condition.py       # Condition tests
│   ├── test_engine.py          # Engine tests
│   ├── test_history.py         # History tests
│   ├── test_rule.py            # Rule tests
│   ├── test_scheduler.py       # Scheduler tests
│   ├── test_templates.py       # Template tests
│   └── test_watcher.py         # Watcher tests
│
├── website/                    # Marketing website
│   ├── index.html              # Landing page
│   ├── privacy.html            # Privacy policy
│   ├── terms.html              # Terms of service
│   ├── cookies.html            # Cookie policy
│   ├── css/styles.css          # Design system
│   └── js/main.js              # Frontend logic
│
├── docs/                       # Documentation
├── pyproject.toml              # Build config
├── requirements.txt            # Dependencies
└── sortmeout.spec              # PyInstaller spec
```

---

## Core Modules

### Rules Engine

**File:** `core/engine.py` (615 lines)

The `RuleEngine` is the heart of SortMeOut. It processes files against an ordered list of rules.

```python
class RuleEngine:
    """
    1. Gathers file information (name, size, dates, tags, content, etc.)
    2. Evaluates each rule's conditions against the file
    3. Executes actions for matching rules
    4. Records results to history
    5. Stops or continues based on rule configuration
    """
```

**Key operations:**

- `process_file(file_path, rules)` → Evaluates all rules against a single file
- License-gated: automation requires active trial or Pro license
- Thread-safe: processes files concurrently
- Preview mode: evaluates rules without executing actions

**Result tracking via `ProcessingResult`:**

- `matched_rules` — which rules matched
- `executed_actions` — results of each action
- `errors` — any errors that occurred
- `processing_time` — duration

### Conditions

**File:** `core/condition.py` (672 lines)

Conditions define the criteria files must meet to match a rule. They support 17 attribute types and numerous operators.

**Attribute Types (`ConditionAttribute`):**

| Category | Attributes |
|----------|------------|
| Name | `NAME`, `EXTENSION`, `FULL_NAME` |
| Path | `PATH`, `PARENT_FOLDER` |
| Size | `SIZE`, `SIZE_BYTES` |
| Dates | `DATE_CREATED`, `DATE_MODIFIED`, `DATE_ACCESSED`, `DATE_ADDED` |
| Type | `FILE_TYPE` (MIME), `KIND` (macOS), `UTI` |
| Content | `CONTENTS` (text search) |
| macOS | `TAGS`, `FINDER_COMMENT`, `WHERE_FROM`, `SPOTLIGHT` |
| Custom | `CUSTOM` (user-defined) |

**Operators (`ConditionOperator`):**

- String: `equals`, `not_equals`, `contains`, `starts_with`, `ends_with`, `matches_regex`, `matches_glob`
- Numeric: `greater_than`, `less_than`, `between`
- List: `in_list`, `not_in_list`
- Date: `before`, `after`, `within_last`, `older_than`
- Boolean: `is_true`, `is_false`
- Existence: `exists`, `not_exists`, `is_empty`, `is_not_empty`

**Condition Groups (`ConditionGroup`):**
Conditions can be combined using logical operators:

- `ALL` — AND logic (all conditions must match)
- `ANY` — OR logic (any condition matches)
- `NONE` — NOT logic (no condition matches)

Groups can be nested for complex boolean expressions.

### Actions

**File:** `core/action.py` (1,241 lines)

Actions define what operations to perform on files that match rule conditions.

**22 Action Types (`ActionType`):**

| Category | Actions |
|----------|---------|
| File Operations | `MOVE`, `COPY`, `RENAME`, `DELETE`, `TRASH` |
| Archive | `ARCHIVE` (zip/tar/gzip), `EXTRACT` |
| macOS Tags | `ADD_TAGS`, `REMOVE_TAGS`, `SET_TAGS` |
| Finder | `SET_COMMENT`, `SET_LABEL`, `REVEAL_IN_FINDER` |
| Apps | `OPEN_WITH`, `IMPORT_TO_PHOTOS`, `IMPORT_TO_MUSIC` |
| Scripts | `RUN_SHELL`, `RUN_APPLESCRIPT`, `RUN_AUTOMATOR`, `RUN_SHORTCUT` |
| Notifications | `NOTIFY` |
| Advanced | `SORT_INTO_SUBFOLDER`, `MAKE_ALIAS`, `TOGGLE_LOCK`, `TOGGLE_EXTENSION` |
| Flow | `NOTHING`, `STOP`, `CONTINUE` |

Each action returns an `ActionResult` with success status, error info, and metadata.

**Rename patterns** support variables like `{name}`, `{ext}`, `{date}`, `{counter}`, `{parent}`.

### Folder Watcher

**File:** `core/watcher.py` (620 lines)

Uses `watchdog` (via macOS FSEvents) for real-time file system monitoring.

**Components:**

- `FileEventHandler` — Filters and debounces file system events
- `FolderWatcher` — Manages a single folder watch
- `WatcherManager` — Manages multiple watchers with thread safety

**Features:**

- Automatic ignore patterns (`.DS_Store`, `.tmp`, `.crdownload`, etc.)
- Debouncing (0.5s default) to avoid duplicate events
- Recursive or non-recursive watching
- Thread-safe start/stop
- License-gated: requires active trial or Pro

### Scheduler

**File:** `core/scheduler.py` (309 lines)

Allows rules to run on a time-based schedule instead of (or in addition to) file system events.

**10 Schedule Intervals:**
`5min`, `15min`, `30min`, `hourly`, `2hours`, `6hours`, `12hours`, `daily`, `weekly`, `monthly`

Each `ScheduledRule` pairs a rule ID with a folder and an interval. The `Scheduler` class runs in a background thread and triggers rule evaluation at the configured intervals.

### History & Undo

**File:** `core/history.py` (713 lines)

All file operations are recorded in a SQLite database for audit trail, undo, and statistics.

**`HistoryManager` features:**

- Thread-safe SQLite operations
- Full undo capability (reverse any recorded action)
- Statistics: actions per day/week/month, top rules, file type distribution
- Query by time range, rule, action type, success/failure
- Automatic cleanup of old entries
- Both the rule engine and AI assistant record through this system

**`HistoryEntry` dataclass:**
Stores timestamp, rule name, action type, source path, destination path, success, error, preview flag, and JSON metadata.

### License System

**File:** `core/license.py` (700 lines)

Singleton `LicenseAuthority` — the single source of truth for all license logic.

**License States:**

- `TRIAL_ACTIVE` — 7-day free trial
- `TRIAL_EXPIRED` — Trial period ended
- `PRO_ACTIVE` — Paid subscription ($9.99/mo)

**Features:**

- Machine fingerprint (hardware UUID) for tamper resistance
- API-based license verification via `api.sortmeout.saidborna.com`
- Rate limiting: Trial = 10 AI calls/day, Pro = 30 AI calls/day
- Feature gates: `can_execute_ai()`, `can_execute_automation()`, `can_watch_filesystem()`
- Stripe integration for payment processing

---

## AI Assistant

### AI Architecture

**File:** `ai/assistant.py` (1,471 lines)

The `FileAssistant` class provides an AI-powered desktop companion using the Anthropic Claude API.

**Models:**

- Default (all users): `claude-sonnet-4-20250514`
- Creator tier: `claude-sonnet-4-5-20250929`

**How it works:**

1. On init, scans the user's folder structure (Documents, Downloads, Desktop, Pictures, etc.) to depth 2
2. On each `chat()` call, builds a system prompt with:
   - Full folder structure as context
   - Detailed file listing of Downloads
   - Current conversation history (last 20 messages)
   - 31 available EXECUTE commands
3. Claude responds with natural language + optional `[EXECUTE: ...]` commands
4. The assistant parses and executes commands, then presents results

**Safety workflow:**

1. AI first presents a plan and asks for confirmation
2. Commands are extracted but NOT executed
3. Only when the user confirms ("yes", "go ahead", "kör") are commands run
4. The `_is_asking_for_confirmation()` guard prevents premature execution

### 31 System Commands

The AI can execute these commands via the `[EXECUTE: command "arg1" "arg2"]` syntax:

| # | Command | Description |
|---|---------|-------------|
| 1 | `mkdir` | Create directories |
| 2 | `move` | Move files to a folder |
| 3 | `copy` | Copy files to a folder |
| 4 | `rename` | Rename a file |
| 5 | `trash` | Move to Trash |
| 6 | `open` | Open file in default app |
| 7 | `openapp` | Launch an application |
| 8 | `search` | Spotlight file search |
| 9 | `tag` | Add a Finder tag |
| 10 | `untag` | Remove a Finder tag |
| 11 | `reveal` | Reveal in Finder |
| 12 | `compress` | Zip a file/folder |
| 13 | `decompress` | Extract a zip archive |
| 14 | `getinfo` | Get detailed file metadata |
| 15 | `emptytrash` | Empty the Trash |
| 16 | `notify` | Send a macOS notification |
| 17 | `clipboard` | Copy text to clipboard |
| 18 | `screenshot` | Take a screenshot |
| 19 | `darkmode` | Toggle dark/light mode |
| 20 | `volume` | Set system volume (0–100) |
| 21 | `mute` | Toggle mute |
| 22 | `preview` | Quick Look a file |
| 23 | `killprocess` | Kill a process by name |
| 24 | `diskspace` | Check disk usage |
| 25 | `battery` | Battery status |
| 26 | `wifi` | WiFi connection info |
| 27 | `lockscreen` | Lock the screen |
| 28 | `say` | Text-to-speech |
| 29 | `eject` | Eject a volume |
| 30 | `symlink` | Create symbolic link |
| 31 | `wallpaper` | Set desktop wallpaper |

Additional info commands (no EXECUTE required): `runningapps`, `foldersize`, `hiddenfiles`.

### Chat Window

**File:** `gui/chat_window.py` (1,165 lines)

A premium native macOS chat interface built entirely with AppKit/PyObjC.

**Design system (matches website):**

- Primary: `#6366F1` (Indigo)
- Secondary: `#8B5CF6` (Purple)
- Background: `#030712` (Gray-950)
- Surface: `#111827` (Gray-900)
- SF Pro fonts (system default)

**Features:**

- `MarkdownRenderer` — Converts markdown (bold, italic, code blocks, headers, bullets, numbered lists, horizontal rules) to `NSAttributedString`
- Animated thinking indicator — 3 wave-pulsing dots with rotating status text ("Analyzing…" → "Thinking…" → "Processing…" → "Reasoning…")
- User identity — reads name from `config.json` → `id -F` → `$USER`
- 🤖 AI emoji branding
- Pill-shaped input bar
- macOS traffic-light button compatibility (centered header to avoid collision)
- Auto-scroll to latest message
- Thread-safe message queue for background API calls

---

## macOS Integration

### Spotlight

**File:** `macos/spotlight.py` (345 lines)

Wraps `mdfind` and `mdls` for Spotlight search and metadata retrieval.

- `search_spotlight(query, folder, limit, attributes)` — Full Spotlight query support
- `get_metadata(file_path)` — All Spotlight attributes for a file (parsed from plist)
- `get_attribute(file_path, attribute)` — Single attribute retrieval
- Input sanitization to prevent query injection

### Finder Tags

**File:** `macos/tags.py` (318 lines)

Full CRUD for macOS Finder tags via `xattr` and plist manipulation.

- `get_tags(file_path)` → list of tag names
- `set_tags(file_path, tags)` → replace all tags
- `add_tags(file_path, tags)` → add tags without removing existing
- `remove_tags(file_path, tags)` → remove specific tags

**Standard tag colors:**
`none` (0), `gray` (1), `green` (2), `purple` (3), `blue` (4), `yellow` (5), `red` (6), `orange` (7)

### Trash Management

**File:** `macos/trash.py` (456 lines)

- `TrashManager` — Full trash lifecycle management
- `TrashItem` dataclass with path, original_path, size, deleted_date, age_days
- `TrashInfo` — Aggregate stats (item count, total size, oldest/newest)
- `get_trash_info()` — Scan trash contents
- `empty_trash()` — Empty trash via AppleScript
- App Sweep functionality for cleaning up orphaned app files

### System Commands

**File:** `macos/system.py` (639 lines)

Comprehensive macOS system automation:

| Function | What it does |
|----------|-------------|
| `reveal_in_finder(path)` | Select file in Finder |
| `quick_look(path)` | Open in Quick Look |
| `compress(path)` | Create .zip via `ditto` |
| `decompress(path)` | Extract .zip via `ditto` |
| `send_notification(title, message)` | macOS notification via `osascript` |
| `clipboard_copy(text)` | Copy to clipboard via `pbcopy` |
| `clipboard_paste()` | Read clipboard via `pbpaste` |
| `take_screenshot(path)` | Capture screen via `screencapture` |
| `toggle_dark_mode()` | Toggle via System Events |
| `get_dark_mode()` | Check current appearance |
| `set_volume(level)` | Set volume 0–100 |
| `get_volume()` | Get current volume |
| `toggle_mute()` | Mute/unmute |
| `get_disk_space()` | Disk usage via `df` |
| `get_battery_info()` | Battery via `pmset` |
| `get_wifi_info()` | WiFi via `networksetup` |
| `lock_screen()` | Lock via System Events |
| `text_to_speech(text)` | Speak via `say` |
| `kill_process(name)` | Kill via `pkill` |
| `eject_volume(name)` | Eject via `diskutil`/Finder |
| `create_symlink(src, dst)` | `os.symlink` |
| `set_wallpaper(path)` | Set via System Events |
| `toggle_hidden_files()` | Show/hide dotfiles in Finder |
| `get_running_apps()` | List apps via System Events |
| `get_folder_size(path)` | Size via `du` |
| `empty_trash_system()` | Empty via Finder AppleScript |
| `get_file_info_detailed(path)` | Full metadata + Spotlight + tags |
| `search_files(query, folder)` | Quick search via `mdfind` |

---

## GUI Layer

### Menu Bar App

**File:** `gui/app.py` (822 lines)

The main entry point for the GUI. Uses `rumps` for macOS menu bar integration.

**Menu structure:**

- **Status** — Watching / Stopped indicator
- **Start/Stop Watching** — Toggle folder monitoring
- **Preview Mode** — Evaluate rules without executing
- **Organize Now** — Run all rules immediately (batch mode)
- **AI Assistant** — Open chat window
- **Analyze File…** — AI analysis of a specific file
- **Folders** — Manage watched folders
- **Rules** — Manage automation rules (with Rule Editor)
- **Templates** — One-click rule templates
- **History** — View recent actions
- **Trash** — Trash info, empty trash, app sweep
- **Settings** — Preferences window
- **License** — Trial/Pro status, activation
- **Quit**

**Onboarding:**
First-run triggers a guided setup that configures initial folders and rules. The `onboarding_completed` flag in `config.json` prevents re-triggering.

### Rule Editor

**File:** `gui/rule_editor.py` (854 lines)

A native AppKit window for visually creating and editing rules.

- Condition builder with dropdowns for attributes, operators, and values
- Action builder with type selection and parameter configuration
- Add/remove rows dynamically
- Match mode selection (ALL/ANY/NONE)
- Enable/disable toggle
- Save/cancel with validation

### Settings Window

**File:** `gui/settings_window.py` (495 lines)

Tabbed preferences window built with AppKit.

**Tabs:**

1. **General** — Startup behavior, default folders
2. **Watcher** — Debounce time, ignore patterns, recursive watching
3. **Trash** — Auto-cleanup age/size, App Sweep
4. **Notifications** — Enable/disable, summary interval, sounds
5. **Logging** — Log level, file logging, rotation
6. **Advanced** — Preview mode, concurrent processing

### Chat Window UI

See [Chat Window](#chat-window) section above. Built with AppKit, features markdown rendering, animated thinking indicator, and full message history.

---

## CLI

**File:** `cli.py` (1,122 lines)

A full-featured terminal interface built with `click` and `rich`.

**Commands:**

```
sortmeout start [--preview] [--foreground]    # Start watching
sortmeout stop                                # Stop watching
sortmeout status                              # Show running status
sortmeout folders list                        # List watched folders
sortmeout folders add <path>                  # Add folder
sortmeout folders remove <path>               # Remove folder
sortmeout rules list                          # List all rules
sortmeout rules add                           # Interactive rule creation
sortmeout rules remove <name>                 # Remove a rule
sortmeout rules enable/disable <name>         # Toggle rule
sortmeout organize <folder> [--preview]       # Run rules on folder now
sortmeout history [--limit N]                 # View action history
sortmeout history stats                       # Statistics
sortmeout history undo <id>                   # Undo an action
sortmeout trash info                          # Trash statistics
sortmeout trash empty                         # Empty trash
sortmeout license status                      # License info
sortmeout license activate <key>              # Activate Pro
sortmeout ai chat                             # Interactive AI chat
sortmeout ai analyze <file>                   # AI file analysis
sortmeout ai suggest <file>                   # AI organization suggestions
```

Uses `rich` for formatted tables, panels, syntax highlighting, and progress bars.

---

## Configuration

**File:** `config/manager.py` (322 lines) + `config/settings.py` (202 lines)

**Config location:** `~/.config/sortmeout/config.json`

The `ConfigManager` handles reading/writing configuration with YAML/JSON support and automatic migration. Settings are type-safe dataclasses:

```python
@dataclass
class Settings:
    watcher: WatcherSettings      # Debounce, ignore patterns, recursive
    trash: TrashSettings          # Auto-cleanup, App Sweep
    notifications: NotificationSettings  # Alerts, summaries, sounds
    logging: LoggingSettings      # Level, file, rotation
```

**Other config files:**

- `~/.config/sortmeout/license.json` — License state, trial dates, machine fingerprint
- `~/.config/sortmeout/folder_structure.json` — Cached folder tree for AI context
- `~/.config/sortmeout/.env` — API keys (Anthropic)
- `~/.sortmeout/history.db` — SQLite action history

---

## Templates

**File:** `core/templates.py` (317 lines)

Pre-built rule templates for quick setup:

| Template | What it does |
|----------|-------------|
| Organize Images | Move JPG/PNG/GIF/HEIC/WebP to `~/Pictures/Downloads` |
| Organize Documents | Move PDF/DOCX/XLSX/PPTX to `~/Documents` |
| Organize Videos | Move MP4/MOV/AVI to `~/Movies` |
| Organize Audio | Move MP3/WAV/FLAC to `~/Music` |
| Organize Archives | Move ZIP/TAR/DMG to a folder |
| Clean Old Downloads | Trash files older than 30 days |
| Screenshots | Move screenshots to `~/Pictures/Screenshots` |
| Large Files Alert | Notify when files > 1GB appear |
| Dev Projects | Organize by project type |
| Installer Cleanup | Trash DMGs after 7 days |

---

## Backend & Payments

**API:** `https://api.sortmeout.saidborna.com` (Cloudflare Workers)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/checkout` | POST | Create Stripe checkout session |
| `/api/verify` | POST | Verify license key |
| `/api/license` | GET | Look up license by email |

**Payment flow:**

1. User clicks "Upgrade to Pro" → app opens Stripe Checkout URL
2. Stripe processes payment → webhook hits Cloudflare Worker
3. Worker generates license key and stores in KV
4. User enters license key → app verifies via `/api/verify`
5. `LicenseAuthority` updates state to `PRO_ACTIVE`

**Website:** [sortmeout.saidborna.com](https://sortmeout.saidborna.com) — Static site on Cloudflare Pages

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.9+ |
| GUI Framework | AppKit/PyObjC (native macOS) |
| Menu Bar | rumps |
| CLI | click + rich |
| File Watching | watchdog (FSEvents backend) |
| AI | Anthropic Claude API (Sonnet 4) |
| Database | SQLite (history) |
| Config | YAML / JSON |
| macOS APIs | mdfind, mdls, xattr, osascript, System Events |
| Backend | Cloudflare Workers (Hono) |
| Payments | Stripe |
| Website | Cloudflare Pages |
| Testing | pytest + pytest-mock + pytest-asyncio |
| Build | PyInstaller |
| Linting | black, isort, flake8, mypy |

**Key dependencies:**

```
watchdog>=3.0.0          # File system monitoring
pyobjc-core>=9.0         # macOS bridge
pyobjc-framework-Cocoa   # AppKit, Foundation
pyobjc-framework-Quartz  # Core Graphics
rumps>=0.4.0             # Menu bar
anthropic>=0.39.0        # Claude AI
pyyaml>=6.0              # Config files
click>=8.0.0             # CLI
rich>=13.0.0             # Terminal formatting
python-dateutil>=2.8.0   # Date parsing
humanize>=4.0.0          # Human-readable values
appdirs>=1.4.0           # OS-specific directories
```

---

## Testing

**207 tests, all passing.**

```
tests/test_action.py      ─  31 tests   (file operations, tags, scripts, archiving)
tests/test_condition.py   ─  49 tests   (all operators, attributes, groups)
tests/test_engine.py      ─  25 tests   (rule processing, license gates, errors)
tests/test_history.py     ─  13 tests   (SQLite CRUD, undo, stats, cleanup)
tests/test_rule.py        ─  31 tests   (serialization, matching, ordering)
tests/test_scheduler.py   ─  18 tests   (intervals, start/stop, edge cases)
tests/test_templates.py   ─  13 tests   (template loading, application)
tests/test_watcher.py     ─  27 tests   (events, debouncing, filtering)
```

Run tests:

```bash
pytest tests/ -q            # Quick run
pytest tests/ -v            # Verbose
pytest tests/ --cov=sortmeout --cov-report=term-missing  # With coverage
```

---

## Building & Distribution

**PyInstaller spec:** `sortmeout.spec`

Build the standalone macOS app:

```bash
pyinstaller sortmeout.spec
```

The built binary is placed in `build/sortmeout/SortMeOut`.

**Development install:**

```bash
pip install -e ".[dev,gui,ai]"
```

**Launch:**

```bash
sortmeout-gui              # GUI (menu bar app)
sortmeout start            # CLI daemon
sortmeout ai chat          # CLI AI chat
```

---

## Installation

### From Source

```bash
git clone https://github.com/S-Borna/sortmeout.git
cd sortmeout
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,gui,ai]"
```

### From Website

Download the latest build from [sortmeout.saidborna.com](https://sortmeout.saidborna.com).

### Requirements

- macOS 12+ (Monterey or later)
- Python 3.9+ (for source install)

---

## License

Proprietary — All rights reserved © 2026 Said Borna

---

**Built with ❤️ for macOS**
