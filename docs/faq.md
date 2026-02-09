# Frequently Asked Questions (FAQ)

Common questions and answers about SortMeOut.

---

## General Questions

### What is SortMeOut?

SortMeOut is an intelligent file automation and AI desktop assistant for macOS. It watches folders you specify and automatically organizes, renames, moves, or processes files based on rules you create. It includes an AI assistant powered by Claude for conversational file management, email, calendar, contacts, presentations, and system control — plus an Image Studio powered by DALL·E 3 for generating and editing images.

### Is SortMeOut free?

SortMeOut offers a **7-day free trial** with full access to all features (5 AI requests/day, 3 image generations/day). After the trial, a **Pro subscription ($9.99/month)** unlocks 30 AI requests/day, 3 image generations/day, priority support, and continued access to all features.

### What macOS versions are supported?

SortMeOut supports macOS 11.0 (Big Sur) and later. Some features may require newer versions for full functionality.

### Does SortMeOut work in the background?

Yes, once started, SortMeOut runs in the background monitoring your specified folders. It can run as a menu bar application or as a background service.

---

## Installation

### How do I install SortMeOut?

The easiest way is via pip:

```bash
pip install sortmeout
```

Or install from source:

```bash
git clone https://github.com/S-Borna/sortmeout.git
cd sortmeout
pip install -e .
```

### Do I need Python installed?

Yes, SortMeOut requires Python 3.9 or later. macOS comes with Python, but you may want to install a newer version via Homebrew:

```bash
brew install python
```

### How do I start SortMeOut automatically at login?

You can add SortMeOut to your Login Items:

1. Open System Preferences > Users & Groups > Login Items
2. Click the + button
3. Navigate to the SortMeOut application or use this command:

```bash
sortmeout config set auto_start true
```

---

## Rules & Conditions

### How many rules can I create?

There's no hard limit. Create as many rules as you need to organize your files effectively.

### What's the difference between "ALL" and "ANY" match modes?

- **ALL**: The file must match every condition in the rule
- **ANY**: The file must match at least one condition
- **NONE**: The file must not match any of the conditions

### Can I use regular expressions in conditions?

Yes! Use the `matches` operator with a regex pattern:

```yaml
conditions:
  - attribute: name
    operator: matches
    value: "^IMG_[0-9]{4}\\.(jpg|png)$"
```

### How do I match files by size?

Use the `size` attribute with units:

```yaml
# Files larger than 100 MB
- attribute: size
  operator: greater_than
  value: "100 MB"

# Files between 10 KB and 1 MB
- attribute: size
  operator: between
  value: "10 KB, 1 MB"
```

Supported units: B, KB, MB, GB, TB

### How do I match files by age?

Use date attributes with duration values:

```yaml
# Modified more than 30 days ago
- attribute: date_modified
  operator: older_than
  value: "30 days"

# Created within the last hour
- attribute: date_created
  operator: newer_than
  value: "1 hour"
```

Supported durations: seconds, minutes, hours, days, weeks, months, years

### Can I create nested conditions?

Yes, use condition groups:

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

---

## Actions

### What happens if the destination folder doesn't exist?

By default, SortMeOut creates the destination folder automatically. You can disable this in the action parameters.

### What if a file with the same name already exists?

You can control this with the `if_exists` parameter:

```yaml
- action_type: move
  params:
    destination: ~/Documents
    if_exists: rename  # Creates "file (1).txt"
    # or: overwrite, skip
```

### Can I run custom scripts?

Yes! Use the `shell` action:

```yaml
- action_type: shell
  params:
    command: "echo 'Processing {full_name}' >> ~/log.txt"
```

Or AppleScript:

```yaml
- action_type: applescript
  params:
    script: |
      tell application "Finder"
        activate
      end tell
```

### What variables can I use in actions?

Available variables:

- `{name}` - Filename without extension
- `{extension}` - File extension
- `{full_name}` - Complete filename
- `{path}` - Full file path
- `{parent_folder}` - Parent folder name
- `{date}` - Current date (YYYY-MM-DD)
- `{time}` - Current time (HH-MM-SS)
- `{year}`, `{month}`, `{day}` - Date components

### Can I chain multiple actions?

Yes, actions execute in order:

```yaml
actions:
  - action_type: add_tags
    params:
      tags: ["Processed"]
  - action_type: rename
    params:
      new_name: "{date}_{name}.{extension}"
  - action_type: move
    params:
      destination: ~/Organized
```

---

## Folders

### How many folders can I watch?

There's no hard limit, but watching too many folders may impact performance. Consider watching parent folders with recursive monitoring instead.

### What's recursive monitoring?

Recursive monitoring watches a folder and all its subfolders. Enable it when adding a folder:

```bash
sortmeout folder add ~/Documents --recursive
```

### Can I exclude certain subfolders?

Yes, use ignore patterns:

```bash
sortmeout folder add ~/Documents --ignore "*.tmp" --ignore "node_modules"
```

### Does SortMeOut process existing files?

By default, SortMeOut only processes new and modified files. To process existing files:

```bash
sortmeout folder process ~/Downloads
```

---

## Performance

### SortMeOut is using too much CPU. What can I do?

Try these optimizations:

1. Reduce the number of watched folders
2. Use more specific conditions to reduce matching
3. Increase the debounce interval in settings
4. Exclude frequently-changing folders (like build directories)

### Why aren't my rules triggering?

Check these common issues:

1. Is SortMeOut running? (`sortmeout status`)
2. Is the folder being watched? (`sortmeout folder list`)
3. Is the rule enabled? (`sortmeout rule list`)
4. Test the file directly: `sortmeout test /path/to/file`
5. Check logs: `sortmeout logs --follow`

### How quickly does SortMeOut process files?

Files are typically processed within 1-2 seconds of appearing. There's a built-in debounce to handle rapid file changes (like during downloads).

---

## Trash Management

### What is App Sweep?

App Sweep finds and removes leftover files when you uninstall an application. It searches for:

- Application Support files
- Preferences
- Caches
- Containers
- Logs

### How do I use App Sweep?

```bash
sortmeout trash clean "AppName.app"
```

Or enable automatic detection in settings.

### Can I automatically empty the Trash?

Yes, configure auto-empty in settings:

```bash
sortmeout config set trash.auto_empty_after "7 days"
```

Files older than the specified age will be permanently deleted.

---

## AI Assistant & Image Studio

### What AI model does SortMeOut use?

SortMeOut uses Anthropic's Claude AI for the assistant and OpenAI's DALL·E 3 for image generation. Both are included with Trial and Pro at no extra cost.

### What can the AI assistant do?

The AI assistant can organize files, search via Spotlight, manage Finder tags, compress archives, control system settings (volume, dark mode, brightness, Bluetooth, WiFi), read and send emails, view and create calendar events, search contacts, create PowerPoint presentations, manage notes and reminders, and 30+ other commands — all from natural language chat.

### How many AI requests do I get?

- **Trial:** 5 AI requests per day + 3 image generations per day
- **Pro:** 30 AI requests per day + 3 image generations per day

Limits reset at midnight UTC. Unused requests don't roll over.

### What is Image Studio?

Image Studio is SortMeOut's built-in image generation and editing suite. Generate images from text prompts using DALL·E 3, then resize, crop, apply filters, add watermarks, and convert between formats — all without leaving the app.

### Is my data sent to external servers?

Only when you explicitly use AI features. File names and your questions are sent to Anthropic's Claude API. Image prompts are sent to OpenAI's DALL·E 3 API. **File contents are never sent.** Generated images are stored locally on your device.

---

## Security & Privacy

### What permissions does SortMeOut need?

For full functionality:

- **Files and Folders**: To read and modify files
- **Full Disk Access**: To access all folders
- **Notifications**: To show alerts (optional)

### Does SortMeOut send data anywhere?

No. SortMeOut is completely offline and doesn't collect or transmit any data.

### Are my rules stored securely?

Rules are stored locally in `~/.config/sortmeout/`. You can encrypt your config folder if desired.

---

## Troubleshooting

### "Permission denied" errors

Grant Full Disk Access:

1. Open System Preferences > Security & Privacy > Privacy
2. Click "Full Disk Access"
3. Add Terminal or SortMeOut to the list
4. Restart SortMeOut

### Rules stopped working after macOS update

1. Re-grant Full Disk Access permissions
2. Restart SortMeOut: `sortmeout stop && sortmeout start`
3. If issues persist, reset and re-import rules:

   ```bash
   sortmeout rule export ~/backup-rules.yaml
   sortmeout config reset
   sortmeout rule import ~/backup-rules.yaml
   ```

### Files aren't being moved/renamed

1. Check destination folder permissions
2. Verify the rule conditions match
3. Check if the file is in use by another application
4. Review the logs for errors

### Menu bar icon not appearing

1. Check System Preferences > Dock & Menu Bar
2. Ensure menu bar extras are allowed
3. Try restarting the GUI: `sortmeout gui --restart`

---

## Feedback & Bug Reports

### Where do I report bugs?

Open an issue on GitHub: <https://github.com/S-Borna/sortmeout/issues>

### How do I request a feature?

Open a feature request on GitHub or create an issue with the "enhancement" label.

---

## Getting Help

### Where can I find more documentation?

- [User Manual](user-manual.md)
- [Rules Guide](rules-guide.md)
- [API Reference](api-reference.md)

### How do I get support?

- **Documentation**: Start here
- **GitHub Issues**: Bug reports
- **GitHub Discussions**: Questions and community help

### Is there a community?

Join discussions on GitHub to connect with other users and share tips.

---

*Still have questions? Open an issue on GitHub!*
