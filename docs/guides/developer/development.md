# Development Guide

**Last Updated:** 2025-11-15
**Target Audience:** Developers
**Difficulty:** Intermediate

## Table of Contents

- [Getting Started](#getting-started)
- [Development Environment Setup](#development-environment-setup)
- [Installing Applications](#installing-applications)
- [Running Applications](#running-applications)
- [Testing](#testing)
- [Code Quality Tools](#code-quality-tools)
- [Development Workflow](#development-workflow)
- [Contributing Guidelines](#contributing-guidelines)
- [Troubleshooting](#troubleshooting)

---

## Getting Started

### Prerequisites

Before you begin, ensure you have:

- **Python 3.8+** installed (`python --version`)
- **pip** package manager (`pip --version`)
- **git** for version control (`git --version`)
- **Virtual environment** tool (recommended)
- **API Credentials** (see [API Setup](#api-credentials-setup))

### Quick Start

```bash
# Clone the repository
git clone <repository-url>
cd music-tools-dev

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install shared library first
cd packages/common
pip install -e ".[dev]"

# Install apps you want to work on
cd ../../apps/music-tools
pip install -e .

# Verify installation
python -c "import music_tools_common; print('Success!')"
```

---

## Development Environment Setup

### 1. Virtual Environment (Recommended)

Using a virtual environment isolates project dependencies:

```bash
# Create virtual environment
python -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate

# Verify activation (should show venv path)
which python

# Deactivate when done
deactivate
```

### 2. Install Development Tools

```bash
# Install workspace-level development tools
pip install black isort flake8 mypy pytest pytest-cov

# Verify installations
black --version
isort --version
flake8 --version
mypy --version
pytest --version
```

### 3. IDE Configuration

#### Visual Studio Code

Create `.vscode/settings.json`:

```json
{
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.mypyEnabled": true,
  "python.formatting.provider": "black",
  "python.formatting.blackArgs": ["--line-length", "100"],
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["apps", "packages"],
  "[python]": {
    "editor.rulers": [100]
  }
}
```

#### PyCharm

1. **Settings > Tools > Black:**
   - Enable "On save"
   - Line length: 100

2. **Settings > Tools > Python Integrated Tools:**
   - Default test runner: pytest
   - Package requirements file: requirements.txt

3. **Settings > Editor > Code Style > Python:**
   - Hard wrap at: 100

### 4. Git Configuration

```bash
# Configure git hooks (optional)
git config core.hooksPath .githooks

# Set up pre-commit hook for code quality
cat > .githooks/pre-commit << 'EOF'
#!/bin/bash
black --check apps/ packages/ || exit 1
isort --check-only apps/ packages/ || exit 1
flake8 apps/ packages/ --max-line-length=100 || exit 1
pytest --maxfail=1 || exit 1
EOF

chmod +x .githooks/pre-commit
```

### 5. API Credentials Setup

#### Spotify API

1. Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
2. Create a new app
3. Get Client ID and Client Secret
4. Add redirect URI: `http://localhost:8888/callback`

#### Deezer

1. Use your Deezer account email
2. No API key needed for basic access

#### Claude AI

Music Country Tagger uses Claude via Claude Max plan (no API key needed)

#### Environment Configuration

Create `.env` file in each app directory:

**apps/music-tools/.env:**
```env
# Spotify
SPOTIPY_CLIENT_ID=your_spotify_client_id
SPOTIPY_CLIENT_SECRET=your_spotify_client_secret
SPOTIPY_REDIRECT_URI=http://localhost:8888/callback

# Deezer
DEEZER_EMAIL=your_deezer_email@example.com

# Paths
MUSIC_TOOLS_CONFIG_DIR=~/.music_tools/config
```

**apps/tag-editor/.env:**
```env
# Last.fm (optional)
LASTFM_API_KEY=your_lastfm_api_key

# Paths
MUSIC_LIBRARY_PATH=/path/to/your/music/library

# Note: Uses Claude via Claude Max plan (no API key needed)
```

**Security Note:** Never commit `.env` files! They're in `.gitignore`.

---

## Installing Applications

### Installation Order

Always install in this order:

1. **Shared packages** (packages/common)
2. **Applications** (apps/*)

### Shared Library (Required)

```bash
cd packages/common

# Development installation (editable mode)
pip install -e ".[dev]"

# Verify installation
python -c "from music_tools_common import config; print('Success!')"
```

**What this installs:**
- Core library with all modules
- Development dependencies (pytest, black, etc.)
- Editable mode (changes take effect immediately)

### Music Tools Application

```bash
cd apps/music-tools

# Install in editable mode
pip install -e .

# Verify installation
python -c "from music_tools_cli import main; print('Success!')"
```

### Install All Available Applications

```bash
# From repository root
pip install -e packages/common[dev]
pip install -e apps/music-tools
# Add other apps as they are migrated to the monorepo structure
```

### Troubleshooting Installation

**Import errors:**
```bash
# Ensure packages/common is installed first
pip list | grep music-tools-common

# Reinstall if needed
pip install -e packages/common --force-reinstall
```

**Dependency conflicts:**
```bash
# Check for conflicts
pip check

# Create fresh virtual environment
deactivate
rm -rf venv
python -m venv venv
source venv/bin/activate
# Reinstall everything
```

---

## Running Applications

### Music Tools

#### Interactive Menu (Recommended)

```bash
cd apps/music-tools
python menu.py
```

Features:
- Spotify Playlist Manager
- Deezer Playlist Checker
- Library Duplicate Detection
- Soundiz File Processor
- Library Comparison Tools

#### Command-Line Interface

```bash
# Library operations
python -m music_tools_cli library index --path ~/Music
python -m music_tools_cli library vet --folder ~/Downloads/new-music
python -m music_tools_cli library stats

# Spotify operations
python -m music_tools_cli spotify --help

# Deezer operations
python -m music_tools_cli deezer --help
```

### Running in Development Mode

```bash
# With debug logging
MUSIC_TOOLS_DEBUG=1 python menu.py

# With verbose output
python menu.py --verbose

# With specific config directory
MUSIC_TOOLS_CONFIG_DIR=/tmp/test_config python menu.py
```

---

## Testing

### Running Tests

#### All Tests

```bash
# From repository root
pytest

# With verbose output
pytest -v

# With coverage
pytest --cov=packages/common --cov=apps
```

#### Specific App Tests

```bash
# Music Tools
pytest apps/music-tools/tests/

# Tag Editor
pytest apps/tag-editor/tests/

# EDM Scraper
pytest apps/edm-scraper/tests/

# Common Library
pytest packages/common/tests/
```

#### Specific Test Files

```bash
# Single test file
pytest packages/common/tests/test_config.py

# Multiple test files
pytest packages/common/tests/test_config.py packages/common/tests/test_database.py
```

#### Specific Tests

```bash
# Single test function
pytest packages/common/tests/test_config.py::test_config_manager_save

# Tests matching pattern
pytest -k "test_spotify"

# Tests with marker
pytest -m "integration"
```

### Test Options

```bash
# Stop on first failure
pytest -x

# Stop after N failures
pytest --maxfail=3

# Run last failed tests
pytest --lf

# Run failed first, then others
pytest --ff

# Show print output
pytest -s

# Parallel testing (requires pytest-xdist)
pytest -n auto
```

### Coverage Reports

```bash
# Generate coverage report
pytest --cov=packages/common --cov=apps

# HTML coverage report
pytest --cov=packages/common --cov=apps --cov-report=html

# Open HTML report
open htmlcov/index.html  # Mac
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows

# Coverage threshold
pytest --cov=packages/common --cov-fail-under=80
```

### Writing Tests

#### Test Structure

```python
# tests/test_feature.py
import pytest
from music_tools_common.config import ConfigManager

class TestConfigManager:
    """Tests for ConfigManager."""

    @pytest.fixture
    def config_manager(self):
        """Create ConfigManager instance."""
        return ConfigManager()

    def test_save_config(self, config_manager):
        """Test saving configuration."""
        # Arrange
        config = {"key": "value"}

        # Act
        config_manager.save_config("test", config)
        loaded = config_manager.load_config("test")

        # Assert
        assert loaded == config
```

#### Test Fixtures

```python
# conftest.py
import pytest
from music_tools_common.database import DatabaseManager

@pytest.fixture
def db():
    """Create temporary database."""
    db = DatabaseManager(":memory:")
    yield db
    db.close()

@pytest.fixture
def sample_playlist():
    """Sample playlist data."""
    return {
        "id": "abc123",
        "name": "Test Playlist",
        "tracks": 50
    }
```

---

## Code Quality Tools

### Black (Code Formatting)

```bash
# Format all code
black apps/ packages/

# Check without modifying
black --check apps/ packages/

# Format specific file
black apps/music-tools/menu.py

# Show what would change
black --diff apps/
```

**Configuration:** `pyproject.toml`
```toml
[tool.black]
line-length = 100
target-version = ['py38', 'py39', 'py310', 'py311']
```

### isort (Import Sorting)

```bash
# Sort all imports
isort apps/ packages/

# Check without modifying
isort --check-only apps/ packages/

# Show differences
isort --diff apps/

# Sort specific file
isort apps/music-tools/menu.py
```

**Configuration:** `pyproject.toml`
```toml
[tool.isort]
profile = "black"
line_length = 100
```

### flake8 (Linting)

```bash
# Lint all code
flake8 apps/ packages/

# With max line length
flake8 apps/ packages/ --max-line-length=100

# Specific file
flake8 apps/music-tools/menu.py

# Show statistics
flake8 --statistics apps/ packages/
```

**Configuration:** `.flake8`
```ini
[flake8]
max-line-length = 100
extend-ignore = E203, W503
exclude = .git,__pycache__,venv,build,dist
```

### mypy (Type Checking)

```bash
# Type check all code
mypy apps/ packages/

# Specific module
mypy packages/common/config/

# Show error codes
mypy --show-error-codes apps/

# Strict mode
mypy --strict packages/common/
```

**Configuration:** `pyproject.toml`
```toml
[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false
ignore_missing_imports = true
```

### Running All Quality Checks

Create a script `scripts/quality-check.sh`:

```bash
#!/bin/bash
set -e

echo "Running Black..."
black --check apps/ packages/

echo "Running isort..."
isort --check-only apps/ packages/

echo "Running flake8..."
flake8 apps/ packages/ --max-line-length=100

echo "Running mypy..."
mypy apps/ packages/

echo "Running tests..."
pytest

echo "All quality checks passed!"
```

Run it:
```bash
chmod +x scripts/quality-check.sh
./scripts/quality-check.sh
```

---

## Development Workflow

### 1. Start New Feature

```bash
# Update main branch
git checkout main
git pull origin main

# Create feature branch
git checkout -b feature/my-new-feature

# Or for bug fixes
git checkout -b fix/bug-description
```

### 2. Make Changes

```bash
# Edit files
vim packages/common/config/manager.py

# Add tests
vim packages/common/tests/test_config.py

# Run tests frequently
pytest packages/common/tests/test_config.py
```

### 3. Quality Checks

```bash
# Format code
black apps/ packages/
isort apps/ packages/

# Lint code
flake8 apps/ packages/ --max-line-length=100

# Type check
mypy packages/common/

# Run tests
pytest
```

### 4. Commit Changes

```bash
# Stage changes
git add packages/common/config/manager.py
git add packages/common/tests/test_config.py

# Commit with descriptive message
git commit -m "feat(config): add support for nested configuration

- Add nested config support to ConfigManager
- Add tests for nested configuration
- Update documentation"
```

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(spotify): add playlist export to CSV
fix(database): handle connection timeout
docs(readme): update installation instructions
test(config): add tests for validation
```

### 5. Push and Create PR

```bash
# Push to remote
git push origin feature/my-new-feature

# Create pull request via GitHub UI or CLI
gh pr create --title "Add new feature" --body "Description"
```

### 6. Code Review

- Address review comments
- Push additional commits
- Wait for CI to pass
- Merge when approved

---

## Contributing Guidelines

### Code Standards

1. **Type Hints:** Use type annotations for all functions
   ```python
   def process_playlist(playlist: dict, service: str) -> bool:
       """Process playlist from service."""
       pass
   ```

2. **Docstrings:** Document all public functions
   ```python
   def save_config(self, name: str, config: dict) -> None:
       """Save configuration to file.

       Args:
           name: Configuration name
           config: Configuration dictionary

       Raises:
           ConfigError: If save fails
       """
       pass
   ```

3. **Error Handling:** Use specific exceptions
   ```python
   try:
       config = load_config(name)
   except FileNotFoundError:
       logger.error(f"Config {name} not found")
       raise ConfigError(f"Configuration {name} not found")
   ```

4. **Logging:** Use logging module, not print
   ```python
   import logging
   logger = logging.getLogger(__name__)

   logger.info("Starting process")
   logger.warning("Deprecated feature used")
   logger.error("Process failed", exc_info=True)
   ```

5. **Testing:** Write tests for new features
   ```python
   def test_new_feature():
       """Test new feature works correctly."""
       # Arrange
       data = create_test_data()

       # Act
       result = new_feature(data)

       # Assert
       assert result.success
       assert result.count == 10
   ```

### Security Guidelines

1. **Never commit secrets:** Use environment variables
2. **Validate input:** Sanitize all user input
3. **Use secure defaults:** Secure file permissions (600/700)
4. **Audit dependencies:** Regular security audits
5. **Review third-party code:** Carefully review dependencies

### Pull Request Checklist

- [ ] Tests added/updated
- [ ] All tests pass
- [ ] Code formatted (black, isort)
- [ ] Linting passes (flake8)
- [ ] Type checking passes (mypy)
- [ ] Documentation updated
- [ ] CHANGELOG updated (if applicable)
- [ ] No secrets committed
- [ ] Branch up to date with main

### Review Process

1. **Self Review:** Review your own changes first
2. **Automated Checks:** Ensure CI passes
3. **Peer Review:** Wait for team review
4. **Address Comments:** Respond to all feedback
5. **Final Approval:** Get approval from maintainer
6. **Merge:** Squash and merge to main

---

## Troubleshooting

### Import Errors

**Problem:** `ModuleNotFoundError: No module named 'music_tools_common'`

**Solution:**
```bash
# Ensure packages/common is installed
cd packages/common
pip install -e ".[dev]"

# Verify installation
pip list | grep music-tools-common
```

### Database Errors

**Problem:** `OperationalError: unable to open database file`

**Solution:**
```bash
# Check config directory exists
mkdir -p ~/.music_tools/config

# Check permissions
chmod 700 ~/.music_tools/config

# Delete corrupted database
rm ~/.music_tools/config/music_tools.db
```

### Authentication Errors

**Problem:** `SpotifyOauthError: invalid_client`

**Solution:**
```bash
# Verify .env file exists
ls apps/music-tools/.env

# Check credentials format
cat apps/music-tools/.env

# Ensure no extra spaces or quotes
SPOTIPY_CLIENT_ID=abc123  # Correct
SPOTIPY_CLIENT_ID="abc123"  # Incorrect
```

### Test Failures

**Problem:** Tests fail with `No module named 'pytest'`

**Solution:**
```bash
# Install dev dependencies
pip install pytest pytest-cov

# Or reinstall with dev extras
cd packages/common
pip install -e ".[dev]"
```

### Permission Errors

**Problem:** `PermissionError: [Errno 13] Permission denied`

**Solution:**
```bash
# Fix ownership
sudo chown -R $USER:$USER ~/.music_tools

# Fix permissions
chmod -R 700 ~/.music_tools
```

### Virtual Environment Issues

**Problem:** Wrong Python version or packages

**Solution:**
```bash
# Deactivate current environment
deactivate

# Delete environment
rm -rf venv

# Create fresh environment
python3.10 -m venv venv
source venv/bin/activate

# Reinstall everything
pip install -e packages/common[dev]
pip install -e apps/music-tools
```

---

## Additional Resources

### Documentation

- [Monorepo Architecture](../architecture/MONOREPO.md)
- [Deployment Guide](DEPLOYMENT.md)
- [API Documentation](../api/)
- [Security Guide](../../SECURITY.md)

### External Resources

- [Python Packaging Guide](https://packaging.python.org/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Black Documentation](https://black.readthedocs.io/)
- [Type Hints Guide](https://docs.python.org/3/library/typing.html)

### Getting Help

- **Documentation:** Check docs/ directory
- **Issues:** Create GitHub issue
- **Discussions:** Use GitHub discussions
- **Security:** Email security@example.com

---

**Last Updated:** 2025-11-15
**Maintained By:** Music Tools Team
**Questions?** Open an issue or discussion on GitHub.
