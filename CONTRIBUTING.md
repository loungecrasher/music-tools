# Contributing to Music Tools Suite

Thank you for your interest in contributing to the Music Tools Suite! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Contribution Workflow](#contribution-workflow)
- [Coding Standards](#coding-standards)
- [Testing Requirements](#testing-requirements)
- [Security Guidelines](#security-guidelines)
- [Commit Message Guidelines](#commit-message-guidelines)
- [Pull Request Process](#pull-request-process)

---

## Code of Conduct

This project adheres to a Code of Conduct that all contributors are expected to follow:

- **Be respectful** of differing viewpoints and experiences
- **Accept constructive criticism** gracefully
- **Focus on what is best** for the community
- **Show empathy** towards other community members

## Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- pip (Python package manager)
- Basic understanding of Python development

### First-Time Contributors

If this is your first contribution:

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/music-tools.git
   cd music-tools
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/ORIGINAL-OWNER/music-tools.git
   ```

## Development Setup

### 1. Install the Shared Library

```bash
cd packages/common
pip install -e ".[dev]"
```

This installs `music_tools_common` in editable mode with all development dependencies.

### 2. Install Pre-commit Hooks

```bash
pre-commit install
```

This ensures code quality checks run automatically before each commit.

### 3. Verify Installation

```bash
# Run tests
pytest

# Check formatting
black --check .
isort --check .

# Type checking
mypy packages/common
```

## Contribution Workflow

### 1. Create a Feature Branch

```bash
git checkout -b feature/your-feature-name
```

Branch naming conventions:
- `feature/` - New features
- `bugfix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Test additions/improvements

### 2. Make Your Changes

- Write clear, concise code
- Follow the coding standards (see below)
- Add tests for new functionality
- Update documentation as needed

### 3. Test Your Changes

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=music_tools_common --cov-report=html

# Check specific module
pytest packages/common/tests/test_config_manager.py
```

### 4. Format and Lint

```bash
# Auto-format code
black .
isort .

# Check for issues
flake8
mypy packages/common
```

### 5. Commit Your Changes

```bash
git add .
git commit -m "feat: Add new feature description"
```

See [Commit Message Guidelines](#commit-message-guidelines) for formatting.

### 6. Push to Your Fork

```bash
git push origin feature/your-feature-name
```

### 7. Create a Pull Request

- Go to GitHub and create a Pull Request
- Fill out the PR template completely
- Link any related issues

## Coding Standards

### Python Style

We follow **PEP 8** with the following configurations:

- **Line length**: 100 characters (configured in pyproject.toml)
- **Formatter**: Black
- **Import sorting**: isort (black profile)
- **Type checking**: mypy

### Code Organization

```python
# Standard library imports
import os
import sys
from pathlib import Path

# Third-party imports
import requests
from rich.console import Console

# Local imports
from music_tools_common.config import ConfigManager
from music_tools_common.database import get_database
```

### Type Hints

**Required** for all public functions and methods:

```python
from typing import Optional, Dict, Any

def fetch_data(
    url: str,
    timeout: int = 30,
    headers: Optional[Dict[str, str]] = None
) -> Optional[Dict[str, Any]]:
    """Fetch data from URL.

    Args:
        url: The URL to fetch
        timeout: Request timeout in seconds
        headers: Optional HTTP headers

    Returns:
        Parsed JSON data or None if request fails

    Raises:
        ValueError: If URL is invalid
        requests.RequestException: If request fails
    """
    pass
```

### Docstrings

Use **Google-style docstrings** for all public functions, classes, and modules:

```python
"""Module for handling Spotify API interactions.

This module provides a client for interacting with the Spotify Web API,
including authentication, playlist management, and track operations.
"""

class SpotifyClient:
    """Client for Spotify Web API.

    Attributes:
        client_id: Spotify application client ID
        client_secret: Spotify application client secret
        redirect_uri: OAuth redirect URI
    """

    def fetch_playlists(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Fetch user's playlists.

        Args:
            limit: Maximum number of playlists to fetch

        Returns:
            List of playlist dictionaries

        Raises:
            SpotifyAuthError: If authentication fails
            SpotifyAPIError: If API request fails
        """
        pass
```

### Error Handling

**Never use bare `except:` clauses**:

```python
# ❌ BAD
try:
    data = json.loads(value)
except:
    return None

# ✅ GOOD
try:
    data = json.loads(value)
except (json.JSONDecodeError, TypeError, ValueError) as e:
    logger.warning(f"Failed to parse JSON: {e}")
    return None
```

### Logging

Use the logger, not print statements:

```python
# ❌ BAD
print(f"Processing file: {filename}")

# ✅ GOOD
logger.info(f"Processing file: {filename}")
```

For sensitive data, use sanitization:

```python
from music_tools_common.utils.security import mask_sensitive_value

logger.info(f"Using API key: {mask_sensitive_value(api_key)}")
```

## Testing Requirements

### Test Coverage

- **New features**: Must include tests (aim for 80%+ coverage)
- **Bug fixes**: Must include regression tests
- **Refactoring**: Maintain or improve existing coverage

### Test Structure

Use pytest with clear test organization:

```python
class TestConfigManager:
    """Tests for ConfigManager class."""

    @pytest.fixture
    def temp_config_dir(self):
        """Create temporary config directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_load_config_success(self, temp_config_dir):
        """Test successful config loading."""
        manager = ConfigManager(config_dir=temp_config_dir)
        # Test implementation...

    def test_load_config_missing_file(self, temp_config_dir):
        """Test config loading when file doesn't exist."""
        # Test implementation...
```

### Running Tests

```bash
# All tests
pytest

# Specific module
pytest packages/common/tests/test_config_manager.py

# With coverage
pytest --cov=music_tools_common --cov-report=html

# Specific test
pytest packages/common/tests/test_config_manager.py::TestConfigManager::test_load_config_success
```

## Security Guidelines

### Never Commit Secrets

- ❌ **Never** commit API keys, passwords, or tokens
- ❌ **Never** commit `.env` files
- ✅ **Always** use `.env.example` for templates
- ✅ **Always** use environment variables for credentials

### Secure File Permissions

```python
# Always set secure permissions for sensitive files
import os

config_file = "~/.music_tools/config/spotify.json"
with open(config_file, 'w') as f:
    json.dump(config, f)
os.chmod(config_file, 0o600)  # Owner read/write only
```

### Input Validation

Always validate user input:

```python
from music_tools_common.utils.security import validate_file_path

# Validate paths to prevent traversal
is_valid, safe_path = validate_file_path(user_path, base_directory="/safe/dir")
if not is_valid:
    raise ValueError(f"Invalid path: {safe_path}")
```

## Commit Message Guidelines

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, etc.)
- **refactor**: Code refactoring
- **test**: Adding or updating tests
- **chore**: Maintenance tasks

### Examples

```
feat(database): Add playlist import/export functionality

Implemented JSON import/export for playlists including:
- Export to JSON file
- Import with duplicate detection
- Validation of imported data

Closes #123
```

```
fix(security): Prevent path traversal in file operations

Added validation to check for path traversal attempts
using '../' sequences. Files outside base directory
are now rejected with clear error messages.

Security impact: HIGH
```

```
docs(readme): Update installation instructions

Clarified Python version requirements and added
troubleshooting section for common import errors.
```

## Pull Request Process

### Before Submitting

1. ✅ All tests pass
2. ✅ Code is formatted (black, isort)
3. ✅ No linting errors (flake8, mypy)
4. ✅ Documentation updated
5. ✅ CHANGELOG.md updated (if applicable)
6. ✅ New tests added for new functionality
7. ✅ No secrets or sensitive data in commits

### PR Template

Fill out all sections:

```markdown
## Description
[Clear description of changes]

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
- [ ] Tests pass locally
- [ ] New tests added
- [ ] Coverage maintained/improved

## Checklist
- [ ] Code follows project style guidelines
- [ ] Documentation updated
- [ ] No new warnings
- [ ] CHANGELOG.md updated
```

### Review Process

1. **Automated checks** must pass (CI/CD)
2. **Code review** by at least one maintainer
3. **Address feedback** promptly
4. **Squash commits** if requested
5. **Maintainer merges** when approved

### After Merge

- Delete your feature branch
- Update your local main branch:
  ```bash
  git checkout main
  git pull upstream main
  ```

## Questions?

- **General questions**: Open a Discussion on GitHub
- **Bug reports**: Open an Issue with the bug template
- **Feature requests**: Open an Issue with the feature template
- **Security issues**: See SECURITY.md for reporting process

---

Thank you for contributing to Music Tools Suite! 🎵

**Maintained by**: Music Tools Team
**License**: MIT
