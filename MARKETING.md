# SortMeOut — Your Mac's Smartest Sidekick

### Automatic file organization + AI desktop assistant for macOS

---

## The Problem

Your Mac is a mess. Downloads is a graveyard of PDFs, screenshots, and mystery files. Documents is a flat folder with 400 items. You spend more time looking for files than working on them.

You've tried folders. You've tried naming conventions. They last about a week.

## The Solution

**SortMeOut watches your folders and organizes files automatically** — the moment they appear. Set rules once, and your Mac stays clean forever.

But SortMeOut is more than a file organizer. It comes with a **built-in AI assistant** that understands your Mac, your files, and what you need — and can actually do something about it.

---

## What Can It Do?

### 📁 Automatic File Organization

Set it and forget it. SortMeOut watches your folders in real-time and sorts files the instant they appear.

- **"PDFs go to Documents/PDFs"** — Done. Every time.
- **"Screenshots go to Pictures/Screenshots"** — Automatically.
- **"Delete downloads older than 30 days"** — Your Mac stays lean.
- **"Move videos larger than 1GB to External Drive"** — Your disk says thank you.

Create rules with 17 conditions (name, type, size, date, content, tags, download source, and more) and 22 actions (move, copy, rename, tag, archive, open with app, run scripts, and more).

### 🤖 AI Desktop Assistant

Talk to your Mac in plain language. The AI assistant is powered by Claude and can actually execute commands — it's not just a chatbot.

**Ask it anything:**

> "Organize my Downloads"
>
> → It scans your files, suggests categories, and moves everything — with your permission.

> "Find my tax documents from 2024"
>
> → Searches via Spotlight and shows you exactly where they are.

> "Compress the Project folder and tag it as Important"
>
> → Zips it and adds a Finder tag. Done.

> "How's my Mac doing?"
>
> → Checks disk space, battery, WiFi, and gives you a full status report.

**31 system commands** the AI can execute:

| What it can do | How it works |
|----------------|-------------|
| Move, copy, rename, trash files | Direct file system operations |
| Search for files | Spotlight integration (mdfind) |
| Add/remove Finder tags | Native macOS tag system |
| Compress & decompress | .zip via macOS ditto |
| Open files & launch apps | Any app on your Mac |
| Take screenshots | Saved to Desktop |
| Send notifications | Native macOS alerts |
| Toggle dark mode | System-wide appearance |
| Set wallpaper | Any image file |
| Control volume & mute | System audio |
| Check battery, disk, WiFi | Full system status |
| Lock screen | Instant lock |
| Text-to-speech | Your Mac reads aloud |
| Kill processes | Force quit any app |
| Eject drives | USB, external drives |
| Quick Look preview | Native file preview |
| Copy to clipboard | Any text |
| Show/hide hidden files | Toggle in Finder |
| Empty trash | With confirmation |
| Create symlinks | File system links |

### ⏰ Scheduled Rules

Not everything needs to happen in real-time. Schedule rules to run every 5 minutes, hourly, daily, weekly, or monthly.

- **Daily:** Clean up temp files
- **Weekly:** Archive old projects
- **Monthly:** Report on disk usage

### 🏷️ Deep macOS Integration

SortMeOut is built for macOS, not ported to it.

- **Spotlight search** — Find any file instantly
- **Finder tags** — Full color-coded tag management
- **Trash management** — Stats, cleanup, App Sweep
- **FSEvents** — Native file system monitoring (not polling)
- **AppleScript** — System-level automation
- **Quick Look** — Preview files without opening

### 🔄 Undo Everything

Every action is recorded. Made a mistake? Undo it. Want to see what happened yesterday? Check the history. Need stats? They're there.

---

## How It Works

### 1. Add folders to watch

Choose which folders SortMeOut monitors — Downloads, Desktop, Documents, or any folder.

### 2. Create rules (or use templates)

Build rules visually with the Rule Editor, or start with pre-built templates:

- **Organize Images** — JPG, PNG, GIF, HEIC → Pictures
- **Organize Documents** — PDF, DOCX, XLSX → Documents
- **Organize Videos** — MP4, MOV, AVI → Movies
- **Clean Old Downloads** — Trash files older than 30 days
- **Screenshot Sorter** — Move screenshots automatically
- And more...

### 3. Let it run

SortMeOut sits in your menu bar, quietly keeping your Mac organized. Check the status anytime, see recent actions, or open the AI assistant for hands-free management.

---

## Two Interfaces

### Menu Bar App

Lives in your menu bar. Start/stop watching, manage rules, open the AI assistant, check history — all from a dropdown.

### Terminal CLI

Full power from the command line:

```
sortmeout start          # Start watching
sortmeout organize ~/Downloads --preview   # Preview what would happen
sortmeout history stats  # See statistics
sortmeout ai chat        # Talk to the AI
```

---

## Built for Privacy

- Your files never leave your Mac — processing is 100% local
- AI conversations use the Claude API (Anthropic) — no data stored on third-party servers
- No telemetry, no analytics, no tracking
- License verification is minimal — a single API call to confirm your key

---

## Pricing

| | Trial | Pro |
|---|---|---|
| **Price** | Free | $9.99/mo |
| **Duration** | 7 days | Unlimited |
| **Rule automation** | ✅ | ✅ |
| **Folder watching** | ✅ | ✅ |
| **AI Assistant** | 5/day | 30/day |
| **All 31 AI commands** | ✅ | ✅ |
| **Templates** | ✅ | ✅ |
| **History & Undo** | ✅ | ✅ |

---

## The Competitive Edge

### vs. Hazel ($42 one-time)

Hazel is great at rules. SortMeOut does rules **and** has an AI assistant that can search, tag, compress, control system settings, and talk to you in natural language. Hazel can't do that.

### vs. Raycast AI

Raycast is a launcher with AI. SortMeOut is a file automation system with AI. We don't replace your launcher — we organize your files and give you system control from a chat window.

### vs. Keyboard Maestro

Keyboard Maestro is powerful but complex. SortMeOut is focused: files and desktop management, done simply. Create a rule in 30 seconds, not 30 minutes.

### What makes SortMeOut unique

No other Mac app combines **rule-based file automation** with a **full AI desktop assistant** in a single, lightweight menu bar app. That's the product.

---

## Technical Highlights

- **15,900 lines** of Python
- **207 tests** passing
- **Native macOS** — AppKit/PyObjC, not Electron
- **Claude Sonnet 4** — latest Anthropic model
- **SQLite** history with full undo
- **Thread-safe** concurrent file processing
- **FSEvents** — real-time, zero-latency file detection
- **Cloudflare Workers** backend — globally distributed
- **Stripe** payments — secure, PCI-compliant

---

## Get Started

**Download:** [sortmeout.saidborna.com](https://sortmeout.saidborna.com)

7-day free trial. No credit card required.

---

*Built by [Said Borna](https://saidborna.com) — for people who believe their Mac should work as hard as they do.*
