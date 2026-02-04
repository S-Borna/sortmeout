# Contributing to SortMeOut

Thank you for your interest in contributing to SortMeOut! This document provides guidelines and instructions for contributing.

---

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Setup](#development-setup)
4. [How to Contribute](#how-to-contribute)
5. [Coding Standards](#coding-standards)
6. [Testing](#testing)
7. [Documentation](#documentation)
8. [Pull Request Process](#pull-request-process)
9. [Release Process](#release-process)

---

## Code of Conduct

This project adheres to a Code of Conduct. By participating, you are expected to:

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on what is best for the community
- Show empathy towards other community members
- Accept constructive criticism gracefully

---

## Getting Started

### Prerequisites

- macOS 11.0 (Big Sur) or later
- Python 3.9 or later
- Git
- A GitHub account

### Fork and Clone

1. Fork the repository on GitHub
2. Clone your fork locally:

   ```bash
   git clone https://github.com/YOUR-USERNAME/sortmeout.git
   cd sortmeout
   ```

3. Add the upstream remote:

   ```bash
   git remote add upstream https://github.com/original/sortmeout.git
   ```

---

## Development Setup

### Create a Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### Install Dependencies

```bash
# Install development dependencies
pip install -e ".[dev]"

# Or install all dependencies manually
pip install -r requirements-dev.txt
```

### Verify Installation

```bash
# Run tests
pytest

# Run the CLI
sortmeout --version
```

### Development Dependencies

The `dev` extras include:

- pytest & pytest-cov - Testing
- black - Code formatting
- isort - Import sorting
- flake8 - Linting
- mypy - Type checking
- pre-commit - Git hooks

### Set Up Pre-commit Hooks

```bash
pre-commit install
```

This ensures code quality checks run before each commit.

---

## How to Contribute

### Reporting Bugs

Before reporting a bug:

1. Search existing issues to avoid duplicates
2. Try to reproduce with the latest version

When reporting, include:

- macOS version
- Python version
- SortMeOut version
- Steps to reproduce
- Expected behavior
- Actual behavior
- Relevant logs or screenshots

Use the bug report template when creating an issue.

### Suggesting Features

We welcome feature suggestions! When suggesting:

- Describe the use case
- Explain expected behavior
- Consider potential drawbacks
- Note if you'd be willing to implement it

Use the feature request template when creating an issue.

### Contributing Code

1. Find or create an issue to work on
2. Comment on the issue to claim it
3. Create a branch for your work
4. Make your changes
5. Test thoroughly
6. Submit a pull request

### Contributing Documentation

Documentation improvements are always welcome:

- Fix typos and errors
- Clarify confusing sections
- Add examples
- Translate to other languages

---

## Coding Standards

### Style Guide

We follow PEP 8 with some modifications:

- Line length: 88 characters (Black default)
- Use type hints
- Write docstrings for public APIs

### Code Formatting

Use Black for code formatting:

```bash
black sortmeout tests
```

Use isort for import sorting:

```bash
isort sortmeout tests
```

### Linting

Run flake8 to check for issues:

```bash
flake8 sortmeout tests
```

### Type Checking

Run mypy for type checking:

```bash
mypy sortmeout
```

### Pre-commit Checks

All checks run automatically via pre-commit:

```bash
pre-commit run --all-files
```

### Code Organization

```
sortmeout/
├── __init__.py          # Package exports
├── app.py               # Main application class
├── core/                # Core functionality
│   ├── rule.py          # Rule class
│   ├── condition.py     # Condition classes
│   ├── action.py        # Action classes
│   ├── engine.py        # Rule engine
│   └── watcher.py       # File watcher
├── config/              # Configuration
│   ├── manager.py       # Config manager
│   └── settings.py      # Settings dataclasses
├── macos/               # macOS integration
│   ├── tags.py          # Finder tags
│   ├── spotlight.py     # Spotlight search
│   └── trash.py         # Trash management
├── utils/               # Utilities
│   ├── logger.py        # Logging
│   └── file_info.py     # File info extraction
├── cli.py               # Command-line interface
└── gui/                 # GUI components
    └── app.py           # Menu bar app
```

### Naming Conventions

- Classes: `PascalCase`
- Functions/methods: `snake_case`
- Constants: `UPPER_SNAKE_CASE`
- Private members: `_leading_underscore`

### Docstrings

Use Google-style docstrings:

```python
def process_file(path: str, preview: bool = False) -> ProcessingResult:
    """Process a file against all rules.

    Args:
        path: Path to the file to process.
        preview: If True, don't execute actions.

    Returns:
        ProcessingResult with success status and details.

    Raises:
        FileNotFoundError: If the file doesn't exist.
        PermissionError: If the file can't be accessed.
    """
```

---

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=sortmeout

# Run specific test file
pytest tests/test_condition.py

# Run specific test
pytest tests/test_condition.py::TestConditionEquality

# Verbose output
pytest -v
```

### Writing Tests

- Place tests in the `tests/` directory
- Name test files `test_*.py`
- Name test classes `Test*`
- Name test methods `test_*`

Example:

```python
import pytest
from sortmeout.core import Condition

class TestConditionEquality:
    """Tests for the equals operator."""

    def test_equals_match(self):
        condition = Condition("name", "equals", "test")
        assert condition.evaluate({"name": "test"})

    def test_equals_no_match(self):
        condition = Condition("name", "equals", "test")
        assert not condition.evaluate({"name": "other"})

    @pytest.mark.parametrize("value", ["Test", "TEST", "TeSt"])
    def test_equals_case_sensitive(self, value):
        condition = Condition("name", "equals", "test")
        assert not condition.evaluate({"name": value})
```

### Test Coverage

Aim for high test coverage:

- New features should have tests
- Bug fixes should include regression tests
- Target >80% coverage

### Integration Tests

For tests requiring macOS features:

```python
import pytest
import platform

@pytest.mark.skipif(
    platform.system() != "Darwin",
    reason="macOS only"
)
def test_finder_tags():
    # Test Finder tag functionality
    pass
```

---

## Documentation

### Documentation Structure

```
docs/
├── user-manual.md       # User guide
├── rules-guide.md       # Rules documentation
├── api-reference.md     # API documentation
├── faq.md               # Frequently asked questions
└── changelog.md         # Version history
```

### Updating Documentation

- Keep docs in sync with code changes
- Use clear, simple language
- Include examples
- Add screenshots for GUI features

### Docstring Updates

When changing public APIs, update docstrings:

```python
def add_rule(self, rule: Rule) -> str:
    """Add a rule to the engine.

    Args:
        rule: The rule to add.

    Returns:
        The ID of the added rule.

    Example:
        >>> engine = RuleEngine()
        >>> rule_id = engine.add_rule(my_rule)
    """
```

---

## Pull Request Process

### Before Submitting

1. ✅ Create/update tests
2. ✅ Run all tests: `pytest`
3. ✅ Format code: `black sortmeout tests`
4. ✅ Sort imports: `isort sortmeout tests`
5. ✅ Run linter: `flake8 sortmeout tests`
6. ✅ Update documentation
7. ✅ Update CHANGELOG.md

### Creating a Pull Request

1. Push your branch to your fork
2. Open a PR against the `main` branch
3. Fill out the PR template completely
4. Link related issues

### PR Title Format

Use conventional commit format:

- `feat: Add new condition operator`
- `fix: Handle empty file names`
- `docs: Update installation guide`
- `test: Add engine tests`
- `refactor: Simplify rule matching`
- `chore: Update dependencies`

### Review Process

1. Automated checks run (CI)
2. Maintainers review the code
3. Address review feedback
4. PR is merged when approved

### After Merge

- Delete your branch
- Sync your fork with upstream
- Celebrate! 🎉

---

## Release Process

### Version Numbering

We follow [Semantic Versioning](https://semver.org/):

- MAJOR: Breaking changes
- MINOR: New features (backward compatible)
- PATCH: Bug fixes

### Release Checklist

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create release notes
4. Tag the release
5. Build and publish to PyPI

---

## Getting Help

### Questions?

- Check the [FAQ](docs/faq.md)
- Search existing issues
- Ask in GitHub Discussions

### Stuck?

- Don't hesitate to ask for help
- Tag maintainers if needed
- We're here to help!

---

## Recognition

Contributors are recognized in:

- CONTRIBUTORS.md
- Release notes
- README acknowledgments

Thank you for contributing to SortMeOut! 🙏
