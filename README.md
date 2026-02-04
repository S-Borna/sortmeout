# SortMeOut 📁✨

An open-source file automation and organization tool for macOS, inspired by Noodlesoft Hazel.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![macOS](https://img.shields.io/badge/platform-macOS-lightgrey.svg)](https://www.apple.com/macos/)

## 🎯 Overview

SortMeOut watches folders you specify and automatically organizes files according to rules you create. Move, rename, tag, archive, or delete files based on name, date, type, content, and much more.

## ✨ Features

### Core Features

- **Folder Watching**: Monitor multiple folders for file changes in real-time
- **Rule-Based Organization**: Create powerful rules with conditions and actions
- **Pattern Matching**: Use glob patterns, regex, and smart matching
- **File Operations**: Move, copy, rename, delete, archive files
- **macOS Integration**: Tags, Spotlight metadata, Finder comments

### Conditions

- File name (contains, starts with, ends with, matches pattern)
- File extension/type (documents, images, videos, etc.)
- File size (greater than, less than, between)
- Date attributes (created, modified, accessed, added)
- File contents (text search, regex)
- macOS tags and Finder comments
- Source URL/application (where downloaded from)
- Nested conditions (AND, OR, NOT logic)

### Actions

- Move to folder (with subfolder creation)
- Copy to folder
- Rename (with pattern substitution)
- Add/remove macOS tags
- Set Finder comments
- Archive (zip, tar, gzip)
- Delete / Move to Trash
- Run shell script
- Execute AppleScript
- Open with application
- Send notification
- Import to Photos/Music

### Advanced Features

- **Trash Management**: Auto-clean trash based on age/size
- **App Sweep**: Detect and remove app support files when uninstalling
- **Preview Mode**: See what rules would do without executing
- **Rule Import/Export**: Share rules with others
- **Logging**: Detailed logs of all operations
- **Menu Bar App**: Quick access and status

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/sortmeout.git
cd sortmeout

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install the application
pip install -e .
```

### Basic Usage

```python
from sortmeout import SortMeOut, Rule, Condition, Action

# Create a new instance
app = SortMeOut()

# Add a folder to watch
app.add_folder("~/Downloads")

# Create a rule to organize PDF files
rule = Rule(
    name="Organize PDFs",
    conditions=[
        Condition("extension", "equals", "pdf")
    ],
    actions=[
        Action("move", destination="~/Documents/PDFs")
    ]
)

# Add rule to the Downloads folder
app.add_rule("~/Downloads", rule)

# Start watching
app.start()
```

### GUI Application

```bash
# Launch the GUI
sortmeout-gui
```

## 📖 Documentation

- [User Manual](docs/user-manual.md)
- [Rule Creation Guide](docs/rules-guide.md)
- [API Reference](docs/api-reference.md)
- [Contributing Guide](CONTRIBUTING.md)
- [FAQ](docs/faq.md)

## 🗺️ Roadmap

### Phase 1: Core Engine (v0.1.0) ✅

- [x] Folder monitoring with FSEvents
- [x] Basic rule engine
- [x] File conditions (name, extension, size, date)
- [x] Basic actions (move, copy, rename, delete)

### Phase 2: Advanced Conditions (v0.2.0)

- [ ] Content-based matching
- [ ] macOS metadata (tags, comments)
- [ ] Download source detection
- [ ] Compound conditions (AND/OR/NOT)

### Phase 3: Advanced Actions (v0.3.0)

- [ ] Archive creation
- [ ] Shell script execution
- [ ] AppleScript integration
- [ ] Notifications

### Phase 4: GUI & UX (v0.4.0)

- [ ] Menu bar application
- [ ] Rule editor interface
- [ ] Preview mode
- [ ] Activity log viewer

### Phase 5: System Features (v0.5.0)

- [ ] Trash management
- [ ] App Sweep functionality
- [ ] Spotlight integration
- [ ] Photos/Music import

### Phase 6: Polish & Release (v1.0.0)

- [ ] Performance optimization
- [ ] Comprehensive testing
- [ ] Documentation complete
- [ ] Community feedback integration

## 🛠️ Development

### Prerequisites

- macOS 10.15 (Catalina) or later
- Python 3.9 or later
- Xcode Command Line Tools

### Setup Development Environment

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Run with coverage
pytest --cov=sortmeout

# Type checking
mypy sortmeout

# Linting
flake8 sortmeout
black sortmeout
```

### Project Structure

```
sortmeout/
├── sortmeout/              # Main package
│   ├── __init__.py
│   ├── app.py              # Main application class
│   ├── core/               # Core functionality
│   │   ├── __init__.py
│   │   ├── watcher.py      # Folder watching (FSEvents)
│   │   ├── rule.py         # Rule definitions
│   │   ├── condition.py    # Condition types
│   │   └── action.py       # Action types
│   ├── conditions/         # Condition implementations
│   ├── actions/            # Action implementations
│   ├── macos/              # macOS-specific integrations
│   ├── gui/                # GUI components
│   ├── utils/              # Utility functions
│   └── config/             # Configuration management
├── tests/                  # Test suite
├── docs/                   # Documentation
├── examples/               # Example rules and scripts
└── resources/              # Icons, assets
```

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Ways to Contribute

- Report bugs and request features via [Issues](https://github.com/yourusername/sortmeout/issues)
- Submit pull requests for bug fixes or new features
- Improve documentation
- Share your custom rules
- Help translate the application

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Inspired by [Noodlesoft Hazel](https://www.noodlesoft.com)
- Built with [watchdog](https://github.com/gorakhargosh/watchdog) for cross-platform file monitoring
- Uses [PyObjC](https://pyobjc.readthedocs.io/) for macOS integration

## 📬 Contact

- GitHub Issues: For bug reports and feature requests
- Discussions: For questions and community support

---

**Note**: This is an independent open-source project and is not affiliated with Noodlesoft.
