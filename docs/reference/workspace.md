# Workspace Quick Reference

**Last Updated:** 2025-11-15

This is a quick reference guide for working in the Music Tools monorepo. For detailed information, see the comprehensive documentation in the `docs/` directory.

## Table of Contents

- [Directory Structure](#directory-structure)
- [Apps vs Packages](#apps-vs-packages)
- [Common Tasks](#common-tasks)
- [Adding New Components](#adding-new-components)
- [Quick Commands](#quick-commands)

---

## Directory Structure

```
Music Tools Dev/                # Monorepo root
│
├── apps/                       # End-user applications
│   ├── music-tools/           # Spotify/Deezer manager
│   ├── tag-editor/            # AI music tagging
│   └── edm-scraper/           # EDM blog scraper
│
├── packages/                   # Shared libraries
│   └── common/                # Common utilities and frameworks
│
├── docs/                       # Documentation
│   ├── architecture/          # Architecture docs and ADRs
│   ├── guides/                # How-to guides
│   └── api/                   # API documentation
│
├── scripts/                    # Utility scripts
├── tools/                      # Development tools
├── .github/workflows/          # CI/CD pipelines
│
├── pyproject.toml             # Workspace configuration
├── README.md                  # Main documentation
├── HOW_TO_RUN.md              # Running instructions
└── WORKSPACE.md               # This file
```

---

## Apps vs Packages

### Apps (apps/)

**What they are:**
- End-user facing applications
- Installable independently with `pip install -e .`
- Have entry points (main.py, cli.py, menu.py)
- Contain user-facing documentation

**Examples:**
- `apps/music-tools/` - Spotify/Deezer playlist manager
- `apps/tag-editor/` - AI-powered music tagging
- `apps/edm-scraper/` - Blog scraping tool

**Key files:**
- `setup.py` - Package definition and dependencies
- `menu.py` or `main.py` - Entry point
- `tests/` - Application-specific tests
- `README.md` - User documentation

### Packages (packages/)

**What they are:**
- Shared libraries used by multiple apps
- No standalone entry points
- Provide reusable functionality
- Test coverage expanding (current: ~35%, target: 80%+)

**Examples:**
- `packages/common/` - Configuration, database, auth, utilities

**Key directories:**
- `config/` - Configuration management
- `database/` - Database and caching
- `auth/` - Authentication (Spotify, Deezer)
- `cli/` - CLI framework
- `utils/` - Utility functions
- `tests/` - Comprehensive test suite

---

## Common Tasks

### Initial Setup

```bash
# Clone repository
git clone <repository-url>
cd "Music Tools Dev"

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install shared library (ALWAYS FIRST)
cd packages/common
pip install -e ".[dev]"

# Install apps you need
cd ../../apps/music-tools
pip install -e .
```

### Daily Development

```bash
# Activate virtual environment
source venv/bin/activate

# Create feature branch
git checkout -b feature/my-feature

# Make changes, add tests

# Run quality checks
black apps/ packages/
isort apps/ packages/
flake8 apps/ packages/ --max-line-length=100
mypy apps/ packages/

# Run tests
pytest

# Commit and push
git add .
git commit -m "feat: add new feature"
git push origin feature/my-feature
```

### Testing

```bash
# All tests
pytest

# Specific app
pytest apps/music-tools/tests/

# Specific package
pytest packages/common/tests/

# With coverage
pytest --cov=packages/common --cov=apps

# Specific test
pytest packages/common/tests/test_config.py::test_save_config
```

### Code Quality

```bash
# Format code
black apps/ packages/
isort apps/ packages/

# Check formatting (no changes)
black --check apps/ packages/
isort --check-only apps/ packages/

# Lint
flake8 apps/ packages/ --max-line-length=100

# Type check
mypy apps/ packages/

# All quality checks
./scripts/quality-check.sh  # If script exists
```

---

## Adding New Components

### Adding a New App

1. **Create directory structure:**

```bash
mkdir -p apps/new-app/{src,tests,config}
cd apps/new-app
```

2. **Create setup.py:**

```python
from setuptools import setup, find_packages

setup(
    name="new-app",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "music-tools-common",  # Shared library
        # Add other dependencies
    ],
)
```

3. **Create main entry point:**

```python
# apps/new-app/main.py
from music_tools_common.cli import BaseCLI

class NewApp(BaseCLI):
    def run(self):
        self.info("Starting new app...")
        # Implementation

if __name__ == "__main__":
    app = NewApp("new-app", "0.1.0")
    exit(app.run())
```

4. **Add tests:**

```python
# apps/new-app/tests/test_main.py
import pytest
from main import NewApp

def test_app_creation():
    app = NewApp("new-app", "0.1.0")
    assert app is not None
```

5. **Add CI/CD job:**

Edit `.github/workflows/ci.yml`:

```yaml
test-new-app:
  name: Test New App
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v3
    - uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    - name: Install dependencies
      run: |
        pip install -e packages/common
        pip install -e apps/new-app
    - name: Run tests
      run: |
        cd apps/new-app
        pytest tests/ -v
```

6. **Install and test:**

```bash
pip install -e apps/new-app
pytest apps/new-app/tests/
```

### Adding New Functionality to Shared Package

1. **Create module:**

```bash
vim packages/common/utils/new_utility.py
```

```python
# packages/common/utils/new_utility.py
def new_function(arg: str) -> str:
    """New utility function.

    Args:
        arg: Input string

    Returns:
        Processed string
    """
    return arg.upper()
```

2. **Add tests:**

```bash
vim packages/common/tests/test_new_utility.py
```

```python
from music_tools_common.utils import new_function

def test_new_function():
    result = new_function("hello")
    assert result == "HELLO"
```

3. **Update __init__.py:**

```python
# packages/common/utils/__init__.py
from .new_utility import new_function

__all__ = ['new_function']
```

4. **Test:**

```bash
pytest packages/common/tests/test_new_utility.py
```

5. **Use in apps:**

```python
from music_tools_common.utils import new_function

result = new_function("test")
```

---

## Quick Commands

### Installation

```bash
# Install everything
pip install -e packages/common[dev]
pip install -e apps/music-tools
pip install -e apps/tag-editor
pip install -e apps/edm-scraper

# Just shared library + one app
pip install -e packages/common[dev]
pip install -e apps/music-tools
```

### Running Apps

```bash
# Music Tools
cd apps/music-tools && python menu.py

# Tag Editor
cd apps/tag-editor && python Codebase/music_tagger/main.py

# EDM Scraper
cd apps/edm-scraper && python cli_scraper.py
```

### Testing

```bash
# Fast: Run all tests
pytest

# With coverage
pytest --cov=packages/common --cov=apps

# Specific tests
pytest apps/music-tools/tests/
pytest -k "test_spotify"
pytest --lf  # Last failed
```

### Code Quality

```bash
# Format (modifies files)
black apps/ packages/
isort apps/ packages/

# Check (no modifications)
black --check apps/ packages/
isort --check-only apps/ packages/
flake8 apps/ packages/ --max-line-length=100
mypy apps/ packages/
```

### Git Workflow

```bash
# Start new feature
git checkout main
git pull origin main
git checkout -b feature/description

# Make changes, test, commit
git add .
git commit -m "feat: description"

# Push and create PR
git push origin feature/description
gh pr create  # If gh CLI installed
```

### Debugging

```bash
# Run with debug logging
MUSIC_TOOLS_DEBUG=1 python menu.py

# Run with specific config
MUSIC_TOOLS_CONFIG_DIR=/tmp/test python menu.py

# Interactive Python
python -i
>>> from music_tools_common import config
>>> config_manager.load_config('spotify')
```

---

## Configuration

### Environment Variables

**Required for all apps:**
```bash
MUSIC_TOOLS_CONFIG_DIR=~/.music_tools/config
```

**For Music Tools:**
```bash
SPOTIPY_CLIENT_ID=your_client_id
SPOTIPY_CLIENT_SECRET=your_client_secret
SPOTIPY_REDIRECT_URI=http://localhost:8888/callback
DEEZER_EMAIL=your_email@example.com
```

**For Tag Editor:**
```bash
# Note: Country Tagger uses Claude via Claude Max plan (no API key needed)
MUSIC_LIBRARY_PATH=/path/to/music
```

### Where to Put .env Files

```
apps/music-tools/.env        # Music Tools config
apps/tag-editor/.env         # Tag Editor config
apps/edm-scraper/.env        # EDM Scraper config
```

**Never commit .env files!** (They're in .gitignore)

---

## Useful File Locations

### Documentation

| File | Purpose |
|------|---------|
| `README.md` | Project overview |
| `HOW_TO_RUN.md` | How to run each app |
| `WORKSPACE.md` | This file - quick reference |
| `docs/architecture/MONOREPO.md` | Architecture guide |
| `docs/guides/DEVELOPMENT.md` | Development guide |
| `docs/guides/DEPLOYMENT.md` | Deployment guide |

### Configuration

| File | Purpose |
|------|---------|
| `pyproject.toml` | Workspace config (pytest, black, isort, mypy) |
| `.gitignore` | Git ignore rules |
| `.github/workflows/ci.yml` | CI/CD pipeline |

### Entry Points

| App | Entry Point |
|-----|-------------|
| Music Tools | `apps/music-tools/menu.py` |
| Tag Editor | `apps/tag-editor/Codebase/music_tagger/main.py` |
| EDM Scraper | `apps/edm-scraper/cli_scraper.py` |

---

## Troubleshooting

### Import Errors

```bash
# Ensure packages/common is installed
pip list | grep music-tools-common

# Reinstall
cd packages/common
pip install -e ".[dev]" --force-reinstall
```

### Test Failures

```bash
# Run single test
pytest packages/common/tests/test_config.py::test_save_config -v

# Show print output
pytest -s

# Stop on first failure
pytest -x
```

### Virtual Environment Issues

```bash
# Recreate environment
deactivate
rm -rf venv
python -m venv venv
source venv/bin/activate
pip install -e packages/common[dev]
```

---

## Getting Help

- **Documentation:** See `docs/` directory
- **Development Guide:** `docs/guides/DEVELOPMENT.md`
- **Architecture:** `docs/architecture/MONOREPO.md`
- **How to Run:** `HOW_TO_RUN.md`
- **Security:** `SECURITY.md`

---

## Quick Links

- [Main README](README.md)
- [Development Guide](docs/guides/DEVELOPMENT.md)
- [Deployment Guide](docs/guides/DEPLOYMENT.md)
- [Monorepo Architecture](docs/architecture/MONOREPO.md)
- [How to Run](getting-started/quick-start.md)
- [Security Guide](guides/operations/security.md)

---

**Last Updated:** 2025-11-15
**Questions?** Check the documentation or open an issue.
