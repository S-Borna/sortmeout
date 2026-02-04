# SortMeOut Rules Guide

A comprehensive guide to creating effective file organization rules.

---

## Table of Contents

1. [Rule Basics](#rule-basics)
2. [Designing Effective Rules](#designing-effective-rules)
3. [Common Rule Patterns](#common-rule-patterns)
4. [Rule Examples](#rule-examples)
5. [Best Practices](#best-practices)
6. [Troubleshooting Rules](#troubleshooting-rules)

---

## Rule Basics

### Anatomy of a Rule

```yaml
name: "Rule Name"           # Descriptive name
match_mode: all             # all, any, or none
priority: 10                # Higher = processed first
enabled: true               # Is rule active?
stop_processing: false      # Stop after match?

conditions:                 # What files to match
  - attribute: extension
    operator: equals
    value: "pdf"

actions:                    # What to do
  - action_type: move
    params:
      destination: ~/Documents/PDFs
```

### How Rules Work

1. **File Detection**: A new/modified file is detected in a watched folder
2. **Rule Matching**: Each enabled rule's conditions are evaluated
3. **Action Execution**: If conditions match, actions are executed in order
4. **Continue/Stop**: Either continue to next rule or stop processing

### Match Modes Explained

#### ALL Mode (Default)

File must satisfy ALL conditions. Use for precise matching.

```yaml
match_mode: all
conditions:
  - attribute: extension
    operator: equals
    value: "pdf"
  - attribute: name
    operator: contains
    value: "invoice"
# Only matches: invoice.pdf, invoice_2024.pdf, my_invoice.pdf
# Does NOT match: report.pdf, invoice.docx
```

#### ANY Mode

File must satisfy at least ONE condition. Use for grouping.

```yaml
match_mode: any
conditions:
  - attribute: extension
    operator: equals
    value: "jpg"
  - attribute: extension
    operator: equals
    value: "png"
  - attribute: extension
    operator: equals
    value: "gif"
# Matches any image file with these extensions
```

#### NONE Mode

File must NOT satisfy any condition. Use for exclusions.

```yaml
match_mode: none
conditions:
  - attribute: name
    operator: starts_with
    value: "."
  - attribute: extension
    operator: equals
    value: "tmp"
# Matches files that are NOT hidden AND NOT temporary
```

---

## Designing Effective Rules

### Start Simple

Begin with a single condition and action:

```yaml
name: "Move Screenshots"
conditions:
  - attribute: name
    operator: starts_with
    value: "Screenshot"
actions:
  - action_type: move
    params:
      destination: ~/Pictures/Screenshots
```

### Add Specificity Gradually

Refine with additional conditions:

```yaml
name: "Move Today's Screenshots"
match_mode: all
conditions:
  - attribute: name
    operator: starts_with
    value: "Screenshot"
  - attribute: date_created
    operator: newer_than
    value: "24 hours"
  - attribute: extension
    operator: equals
    value: "png"
actions:
  - action_type: move
    params:
      destination: ~/Pictures/Screenshots/Today
```

### Use Condition Groups for Complex Logic

```yaml
name: "Organize Media"
conditions:
  # Main condition: must be a media file
  - type: group
    match_mode: any
    conditions:
      - attribute: extension
        operator: in_list
        value: ["jpg", "png", "gif"]
      - attribute: extension
        operator: in_list
        value: ["mp4", "mov", "avi"]
      - attribute: extension
        operator: in_list
        value: ["mp3", "wav", "flac"]
actions:
  - action_type: move
    params:
      destination: ~/Media
```

---

## Common Rule Patterns

### Pattern 1: Sort by File Type

```yaml
# Images
name: "Sort Images"
conditions:
  - attribute: extension
    operator: in_list
    value: ["jpg", "jpeg", "png", "gif", "webp", "heic"]
actions:
  - action_type: move
    params:
      destination: ~/Pictures

# Documents
name: "Sort Documents"
conditions:
  - attribute: extension
    operator: in_list
    value: ["pdf", "doc", "docx", "txt", "rtf"]
actions:
  - action_type: move
    params:
      destination: ~/Documents
```

### Pattern 2: Date-Based Organization

```yaml
name: "Organize by Month"
conditions:
  - attribute: date_created
    operator: exists
actions:
  - action_type: move
    params:
      destination: "~/Organized/{year}/{month}"
```

### Pattern 3: Size-Based Handling

```yaml
# Large files to external drive
name: "Move Large Files"
conditions:
  - attribute: size
    operator: greater_than
    value: "1 GB"
actions:
  - action_type: move
    params:
      destination: /Volumes/External/Large Files

# Compress medium files
name: "Compress Medium Files"
conditions:
  - attribute: size
    operator: between
    value: "100 MB, 1 GB"
actions:
  - action_type: archive
    params:
      format: zip
```

### Pattern 4: Name-Based Routing

```yaml
name: "Route Work Files"
conditions:
  - attribute: name
    operator: matches
    value: "^(work|project|client)_.*"
actions:
  - action_type: move
    params:
      destination: ~/Work

name: "Route Personal Files"
conditions:
  - attribute: name
    operator: matches
    value: "^(personal|family|vacation)_.*"
actions:
  - action_type: move
    params:
      destination: ~/Personal
```

### Pattern 5: Cleanup Rules

```yaml
name: "Remove Old Downloads"
conditions:
  - attribute: date_modified
    operator: older_than
    value: "90 days"
actions:
  - action_type: trash

name: "Delete Temporary Files"
conditions:
  - attribute: extension
    operator: in_list
    value: ["tmp", "temp", "bak", "cache"]
actions:
  - action_type: delete
    params:
      force: true
```

---

## Rule Examples

### Download Manager

```yaml
# Process completed downloads
name: "Completed Downloads"
conditions:
  - attribute: extension
    operator: not_in_list
    value: ["crdownload", "part", "download"]
  - attribute: date_added
    operator: newer_than
    value: "5 minutes"
actions:
  - action_type: notify
    params:
      title: "Download Complete"
      message: "{full_name} is ready"
```

### Photo Organization

```yaml
name: "Organize Photos by Date"
conditions:
  - attribute: extension
    operator: in_list
    value: ["jpg", "jpeg", "heic", "png", "raw"]
actions:
  - action_type: rename
    params:
      new_name: "{date}_{name}.{extension}"
  - action_type: move
    params:
      destination: "~/Pictures/{year}/{month}"
```

### Invoice Processing

```yaml
name: "Process Invoices"
conditions:
  - attribute: name
    operator: contains
    value: "invoice"
  - attribute: extension
    operator: equals
    value: "pdf"
actions:
  - action_type: add_tags
    params:
      tags: ["Invoice", "Finance"]
  - action_type: rename
    params:
      new_name: "{date}_invoice_{name}.pdf"
  - action_type: copy
    params:
      destination: ~/Documents/Invoices
  - action_type: copy
    params:
      destination: ~/Dropbox/Accounting
```

### Development Project Cleanup

```yaml
name: "Clean Build Artifacts"
conditions:
  - attribute: extension
    operator: in_list
    value: ["o", "pyc", "class"]
actions:
  - action_type: delete
    params:
      force: true

name: "Archive Old Logs"
conditions:
  - attribute: extension
    operator: equals
    value: "log"
  - attribute: size
    operator: greater_than
    value: "10 MB"
actions:
  - action_type: archive
    params:
      format: "tar.gz"
      delete_original: true
```

### Email Attachment Organization

```yaml
name: "Sort Email Attachments"
conditions:
  - attribute: parent_folder
    operator: equals
    value: "Mail Downloads"
actions:
  - action_type: add_tags
    params:
      tags: ["Email"]
  - action_type: shell
    params:
      command: |
        # Extract date from filename if present
        DATE=$(echo "{name}" | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}')
        if [ -n "$DATE" ]; then
          mkdir -p ~/Documents/Email/$DATE
          mv "{path}" ~/Documents/Email/$DATE/
        fi
```

### Application Installer Cleanup

```yaml
name: "Clean Installers After Use"
conditions:
  - attribute: extension
    operator: in_list
    value: ["dmg", "pkg", "app"]
  - attribute: date_added
    operator: older_than
    value: "7 days"
actions:
  - action_type: notify
    params:
      title: "Old Installer Found"
      message: "{full_name} - Consider removing"
  - action_type: add_tags
    params:
      tags: ["Old Installer"]
```

---

## Best Practices

### 1. Use Descriptive Names

```yaml
# Good
name: "Archive Old Financial Reports to External Drive"

# Not so good
name: "Rule 1"
```

### 2. Set Appropriate Priorities

```yaml
# More specific rules should have higher priority
name: "Work Invoices"
priority: 100

name: "All PDFs"
priority: 10
```

### 3. Use Preview Mode First

Always test rules in preview mode before enabling:

```bash
sortmeout start --preview
```

### 4. Handle Conflicts Gracefully

```yaml
actions:
  - action_type: move
    params:
      destination: ~/Documents
      if_exists: rename  # or: overwrite, skip
```

### 5. Add Notifications for Important Actions

```yaml
actions:
  - action_type: delete
    params:
      force: true
  - action_type: notify
    params:
      title: "File Deleted"
      message: "Removed: {full_name}"
```

### 6. Group Related Rules

Keep related rules together with consistent naming:

```yaml
name: "Media - Sort Images"
name: "Media - Sort Videos"
name: "Media - Sort Audio"
name: "Work - Sort Documents"
name: "Work - Sort Spreadsheets"
```

### 7. Use stop_processing Wisely

```yaml
# Catch-all rule at the end
name: "Default Handler"
priority: 0
stop_processing: true  # Don't process further
actions:
  - action_type: add_tags
    params:
      tags: ["Unsorted"]
```

### 8. Back Up Your Rules

```bash
sortmeout rule export ~/backup/rules.yaml
```

---

## Troubleshooting Rules

### Rule Not Matching

1. **Check if rule is enabled**

   ```bash
   sortmeout rule list
   ```

2. **Test the file directly**

   ```bash
   sortmeout test /path/to/file.txt
   ```

3. **Check conditions one by one**
   - Are attribute names correct?
   - Is the operator appropriate?
   - Are values formatted correctly?

4. **Verify match mode**
   - `all`: ALL conditions must match
   - `any`: At least ONE must match

### Actions Not Executing

1. **Check action parameters**
   - Destination folder exists?
   - Correct permissions?

2. **Check for file conflicts**
   - File already exists at destination?
   - Set `if_exists` parameter

3. **Check action order**
   - Actions execute sequentially
   - A failed action may stop the chain

### Performance Issues

1. **Too many rules?**
   - Combine similar rules
   - Use condition groups

2. **Too many watched folders?**
   - Watch parent folders instead
   - Use recursive watching wisely

3. **Complex regex patterns?**
   - Simplify patterns
   - Use simpler operators when possible

### Debugging Tips

```bash
# Enable verbose logging
sortmeout start --verbose

# Check logs
tail -f ~/Library/Logs/SortMeOut/sortmeout.log

# Test specific rule
sortmeout test /path/to/file --rule "Rule Name"
```

---

## Quick Reference Card

### Operators

| Type | Operators |
|------|-----------|
| String | equals, not_equals, contains, not_contains, starts_with, ends_with, matches |
| Numeric | greater_than, less_than, between |
| Date | older_than, newer_than, before, after |
| List | in_list, not_in_list |
| Existence | exists, not_exists, is_empty, is_not_empty |

### Common Attributes

| Attribute | Use For |
|-----------|---------|
| extension | File type matching |
| name | Filename patterns |
| size | Size-based rules |
| date_modified | Age-based cleanup |
| tags | Tag-based organization |

### Action Types

| Action | Use For |
|--------|---------|
| move | Relocate files |
| copy | Create backups |
| rename | Organize by naming |
| archive | Compress files |
| trash | Safe deletion |
| add_tags | Categorization |
| notify | User alerts |
| shell | Custom scripts |

---

*Happy organizing with SortMeOut!*
