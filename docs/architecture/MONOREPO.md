# Monorepo Architecture

**Last Updated:** 2025-11-15
**Status:** Production Ready
**Version:** 1.0.0

## Table of Contents

- [Overview](#overview)
- [Why Monorepo?](#why-monorepo)
- [Directory Organization](#directory-organization)
- [Apps vs Packages](#apps-vs-packages)
- [Development Workflow](#development-workflow)
- [Testing Strategy](#testing-strategy)
- [CI/CD Pipeline](#cicd-pipeline)
- [Dependencies Management](#dependencies-management)
- [Best Practices](#best-practices)

---

## Overview

The Music Tools Suite is organized as a **monorepo** - a single repository containing multiple related applications (`apps/`) and shared libraries (`packages/`). This architecture enables code sharing, unified tooling, and streamlined development across all Music Tools projects.

### Key Characteristics

- **Single Repository:** All applications and shared code in one repository
- **Shared Dependencies:** Common libraries are shared across applications
- **Unified Tooling:** Single configuration for testing, linting, and formatting
- **Atomic Changes:** Changes across multiple apps/packages in single commits
- **Consistent Standards:** Unified code quality and security standards

---

## Why Monorepo?

The monorepo structure was chosen for several compelling reasons:

### 1. **Code Reuse and DRY Principle**

**Before Monorepo:**
- Each application had duplicate code for:
  - Configuration management
  - Database operations
  - Authentication (Spotify, Deezer)
  - Utility functions
  - CLI frameworks
- Approximately 70% code duplication across projects

**After Monorepo:**
- All shared code consolidated in `packages/common`
- Applications focus on unique functionality
- Code reduction of 60-75% in individual apps
- Single source of truth for common operations

### 2. **Unified Development Experience**

- **Single Setup:** One command installs all dependencies
- **Consistent Tooling:** Same linting, formatting, and testing tools
- **Shared Standards:** Unified code style and quality standards
- **Simplified Onboarding:** New developers learn one structure

### 3. **Atomic Cross-Project Changes**

- Modify shared library and dependent apps in one commit
- Guaranteed compatibility across all applications
- No version synchronization headaches
- Easier to maintain consistency

### 4. **Simplified Dependency Management**

- Centralized dependency definitions
- Easier to update and audit dependencies
- Reduced risk of version conflicts
- Single security audit process

### 5. **Streamlined CI/CD**

- One workflow configuration for all apps
- Parallel testing across applications
- Conditional job execution (only test changed apps)
- Unified deployment process

### 6. **Better Collaboration**

- Single repository for all code
- Cross-application code reviews
- Shared knowledge base
- Easier to discover related functionality

---

## Directory Organization

```
Music Tools Dev/                    # Repository root
├── .github/                        # GitHub configuration
│   └── workflows/
│       └── ci.yml                  # CI/CD pipeline
│
├── apps/                           # Application code (end-user facing)
│   ├── music-tools/                # Spotify/Deezer management app
│   ├── tag-editor/                 # AI-powered music tagging app
│   └── edm-scraper/                # EDM blog scraping app
│
├── packages/                       # Shared libraries (internal)
│   └── common/                     # Common utilities and frameworks
│
├── docs/                           # Project-wide documentation
│   ├── architecture/               # Architecture decisions and design
│   ├── guides/                     # How-to guides
│   └── api/                        # API documentation
│
├── scripts/                        # Repository-wide utility scripts
├── tools/                          # Development tools
│   └── code-quality/               # Linting and formatting configs
│
├── pyproject.toml                  # Workspace-level configuration
├── .gitignore                      # Git ignore rules
├── README.md                       # Main project documentation
└── WORKSPACE.md                    # Quick workspace reference
```

### Directory Purposes

| Directory | Purpose | Contents |
|-----------|---------|----------|
| **apps/** | End-user applications | Deployable applications with user interfaces |
| **packages/** | Shared libraries | Internal libraries used by apps |
| **docs/** | Documentation | Architecture, guides, API docs |
| **scripts/** | Automation | Build, deployment, maintenance scripts |
| **tools/** | Development | Code quality tools and configs |
| **.github/** | CI/CD | GitHub Actions workflows |

---

## Apps vs Packages

Understanding the distinction between `apps/` and `packages/` is crucial:

### Apps (apps/)

**Definition:** End-user facing applications that can be installed and run independently.

**Characteristics:**
- Have their own entry points (main.py, cli.py, etc.)
- Can be installed as standalone applications
- May have their own configuration files
- Include user-facing documentation
- Depend on packages but not on other apps

**Examples:**
```
apps/music-tools/          # Spotify/Deezer playlist manager
├── setup.py               # Installable package
├── main.py                # Entry point
├── menu.py                # User interface
├── config/                # App-specific config
├── tests/                 # App-specific tests
└── README.md              # User documentation
```

**When to Create an App:**
- Building a new user-facing tool
- Creating a new CLI application
- Developing a web service/API
- Building a standalone utility

### Packages (packages/)

**Definition:** Shared libraries providing functionality used by multiple apps.

**Characteristics:**
- No standalone entry points
- Installed as dependencies of apps
- Provide reusable functionality
- Well-tested with high coverage
- Minimal external dependencies

**Examples:**
```
packages/common/           # Shared library
├── setup.py               # Installable package
├── config/                # Config management
├── database/              # Database operations
├── auth/                  # Authentication
├── utils/                 # Utilities
└── tests/                 # Comprehensive tests
```

**When to Create a Package:**
- Code is used by 2+ applications
- Functionality is generic/reusable
- Creating a new framework/library
- Abstracting common patterns

### Dependency Flow

```
┌─────────────────┐
│  apps/music-tools│
└────────┬─────────┘
         │ depends on
         ▼
┌─────────────────┐
│packages/common  │
└─────────────────┘
         ▲
         │ depends on
         │
┌────────┴─────────┐
│  apps/tag-editor │
└──────────────────┘
```

**Rules:**
1. Apps can depend on packages
2. Apps cannot depend on other apps
3. Packages can depend on other packages
4. All dependencies must be explicit in setup.py

---

## Development Workflow

### Initial Setup

```bash
# 1. Clone repository
git clone <repository-url>
cd "Music Tools Dev"

# 2. Install shared packages first
cd packages/common
pip install -e ".[dev]"

# 3. Install apps you want to work on
cd ../../apps/music-tools
pip install -e .

cd ../tag-editor
pip install -e .

cd ../edm-scraper
pip install -e .
```

### Daily Development

```bash
# Start working on a feature
git checkout -b feature/my-new-feature

# Make changes to code
# Edit files in apps/ or packages/

# Run tests for affected apps
pytest apps/music-tools/tests/
pytest packages/common/tests/

# Format code
black apps/ packages/
isort apps/ packages/

# Check types
mypy apps/ packages/

# Commit changes
git add .
git commit -m "feat: add new feature"

# Push and create PR
git push origin feature/my-new-feature
```

### Working Across Apps and Packages

**Scenario:** Adding a new utility function used by multiple apps

```bash
# 1. Add function to shared package
vim packages/common/utils/new_utility.py

# 2. Add tests
vim packages/common/tests/test_new_utility.py
pytest packages/common/tests/

# 3. Use in apps
vim apps/music-tools/src/feature.py
vim apps/tag-editor/src/feature.py

# 4. Test all affected apps
pytest apps/music-tools/tests/
pytest apps/tag-editor/tests/

# 5. Commit everything atomically
git add .
git commit -m "feat: add new utility function"
```

### Code Review Process

1. **Create Feature Branch:** `git checkout -b feature/description`
2. **Make Changes:** Edit code, add tests, update docs
3. **Run Quality Checks:** black, isort, flake8, mypy, pytest
4. **Push Changes:** `git push origin feature/description`
5. **Create Pull Request:** Use GitHub UI
6. **CI Checks:** Automated tests and linting
7. **Code Review:** Team reviews changes
8. **Merge:** Squash and merge to main

---

## Testing Strategy

### Test Organization

```
Music Tools Dev/
├── apps/
│   ├── music-tools/
│   │   └── tests/              # App-specific tests
│   │       ├── test_spotify.py
│   │       ├── test_deezer.py
│   │       └── conftest.py
│   └── tag-editor/
│       └── tests/              # App-specific tests
│
└── packages/
    └── common/
        └── tests/              # Library tests
            ├── test_config.py
            ├── test_database.py
            └── conftest.py
```

### Test Types

#### 1. Unit Tests

**Purpose:** Test individual functions and classes in isolation

**Location:** Alongside the code being tested

**Example:**
```python
# packages/common/tests/test_config.py
def test_config_manager_save():
    """Test saving configuration."""
    manager = ConfigManager()
    config = {"key": "value"}
    manager.save_config("test", config)
    loaded = manager.load_config("test")
    assert loaded == config
```

#### 2. Integration Tests

**Purpose:** Test interactions between components

**Location:** In app or package tests directory

**Example:**
```python
# apps/music-tools/tests/test_integration.py
def test_spotify_to_database():
    """Test saving Spotify playlists to database."""
    sp = get_spotify_client()
    db = get_database()

    playlists = sp.current_user_playlists()
    for playlist in playlists['items']:
        db.add_playlist(playlist, 'spotify')

    saved = db.get_playlists(service='spotify')
    assert len(saved) > 0
```

#### 3. End-to-End Tests

**Purpose:** Test complete user workflows

**Location:** In app tests directory

**Example:**
```python
# apps/music-tools/tests/test_e2e.py
def test_playlist_export_workflow():
    """Test complete playlist export workflow."""
    # Authenticate
    sp = get_spotify_client()

    # Fetch playlists
    playlists = fetch_all_playlists(sp)

    # Save to database
    save_playlists(playlists)

    # Export to CSV
    export_to_csv(playlists, "output.csv")

    # Verify CSV
    assert os.path.exists("output.csv")
```

### Running Tests

```bash
# Run all tests from repository root
pytest

# Run specific app tests
pytest apps/music-tools/tests/

# Run specific package tests
pytest packages/common/tests/

# Run with coverage
pytest --cov=packages/common --cov=apps/music-tools

# Run specific test file
pytest packages/common/tests/test_config.py

# Run specific test
pytest packages/common/tests/test_config.py::test_config_manager_save

# Run tests matching pattern
pytest -k "test_spotify"

# Run with verbose output
pytest -v

# Run with output captured
pytest -s
```

### Test Coverage Goals

| Component | Coverage Target | Current |
|-----------|----------------|---------|
| **packages/common** | 90%+ | 90%+ |
| **apps/music-tools** | 80%+ | 75% |
| **apps/tag-editor** | 70%+ | 60% |
| **apps/edm-scraper** | 70%+ | 50% |

### Testing Best Practices

1. **Write Tests First:** TDD approach when possible
2. **Test One Thing:** Each test should verify one behavior
3. **Use Fixtures:** Share common setup with pytest fixtures
4. **Mock External APIs:** Don't hit real APIs in tests
5. **Fast Tests:** Keep tests fast (<1s per test)
6. **Clear Names:** Test names should describe what they test
7. **Arrange-Act-Assert:** Follow AAA pattern

---

## CI/CD Pipeline

### GitHub Actions Workflow

The monorepo uses a single GitHub Actions workflow (`.github/workflows/ci.yml`) with multiple jobs:

```yaml
jobs:
  test-music-tools:     # Test music-tools app
  test-tag-editor:      # Test tag-editor app
  test-edm-scraper:     # Test edm-scraper app
  lint:                 # Lint all code
```

### Conditional Execution

Jobs only run when relevant files change:

```yaml
if: contains(github.event.head_commit.modified, 'apps/music-tools') ||
    contains(github.event.head_commit.modified, 'packages/common')
```

### Pipeline Stages

#### 1. Setup (All Jobs)

```yaml
- uses: actions/checkout@v3
- uses: actions/setup-python@v4
  with:
    python-version: '3.10'
```

#### 2. Install Dependencies

```yaml
- name: Install dependencies
  run: |
    pip install -e packages/common
    pip install -e apps/music-tools
```

#### 3. Run Tests

```yaml
- name: Run tests
  run: |
    cd apps/music-tools
    pytest tests/ -v
```

#### 4. Lint Code

```yaml
- name: Run black
  run: black --check apps/ packages/

- name: Run isort
  run: isort --check-only apps/ packages/

- name: Run flake8
  run: flake8 apps/ packages/ --max-line-length=100
```

### Adding CI/CD for New Apps

1. **Add test job** to `.github/workflows/ci.yml`:

```yaml
test-new-app:
  name: Test New App
  runs-on: ubuntu-latest
  if: contains(github.event.head_commit.modified, 'apps/new-app')

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

### Deployment Pipeline (Future)

```yaml
deploy:
  name: Deploy Applications
  needs: [test-music-tools, test-tag-editor, lint]
  runs-on: ubuntu-latest
  if: github.ref == 'refs/heads/main'

  steps:
    - name: Deploy to production
      run: |
        # Deployment steps here
```

---

## Dependencies Management

### Dependency Levels

The monorepo has three levels of dependencies:

#### 1. Workspace-Level (Root)

**File:** `pyproject.toml`

**Purpose:** Development tools used across all apps/packages

```toml
[tool.pytest.ini_options]
testpaths = ["apps", "packages"]

[tool.black]
line-length = 100

[tool.mypy]
python_version = "3.10"
```

**Installation:**
```bash
pip install black isort flake8 mypy pytest
```

#### 2. Package-Level

**File:** `packages/common/setup.py`

**Purpose:** Dependencies for shared library

```python
install_requires=[
    "requests>=2.31.0",
    "pydantic>=2.12.0",
    "python-dotenv>=1.0.0",
    "spotipy>=2.25.0",
]
```

**Installation:**
```bash
cd packages/common
pip install -e ".[dev]"
```

#### 3. App-Level

**File:** `apps/music-tools/setup.py`

**Purpose:** App-specific dependencies

```python
install_requires=[
    "music-tools-common",  # Local package
    "click>=8.3.0",
    "rich>=14.2.0",
]
```

**Installation:**
```bash
cd apps/music-tools
pip install -e .
```

### Dependency Resolution

```
Root pyproject.toml (dev tools)
    ↓
packages/common/setup.py (library deps)
    ↓
apps/music-tools/setup.py (app deps)
```

### Adding Dependencies

#### To Shared Package:

```bash
cd packages/common
vim requirements.txt  # Add dependency
vim setup.py          # Update install_requires
pip install -e .      # Reinstall
pytest                # Verify tests pass
```

#### To Application:

```bash
cd apps/music-tools
vim requirements.txt  # Add dependency
vim setup.py          # Update install_requires
pip install -e .      # Reinstall
pytest                # Verify tests pass
```

### Dependency Audit

```bash
# Check for security vulnerabilities
pip audit

# List all dependencies
pip freeze > requirements-freeze.txt

# Check for outdated packages
pip list --outdated

# Update all dependencies
pip install --upgrade -r requirements.txt
```

---

## Best Practices

### 1. Code Organization

- **Keep apps focused:** Each app should have a single, clear purpose
- **Share common code:** Move duplicate code to packages/common
- **Use clear naming:** Descriptive names for modules and functions
- **Follow structure:** Maintain consistent directory structure

### 2. Version Control

- **Atomic commits:** Related changes in one commit
- **Clear messages:** Descriptive commit messages
- **Feature branches:** Use branches for new features
- **Small PRs:** Keep pull requests focused and reviewable

### 3. Testing

- **Test everything:** Aim for high coverage
- **Fast tests:** Keep test suite fast
- **Mock external services:** Don't hit real APIs
- **Continuous testing:** Run tests frequently

### 4. Documentation

- **Keep docs updated:** Update docs with code changes
- **Document decisions:** Use ADRs for important decisions
- **Clear examples:** Include code examples in docs
- **Link related docs:** Cross-reference documentation

### 5. Security

- **Never commit secrets:** Use environment variables
- **Audit dependencies:** Regular security audits
- **Secure permissions:** Proper file permissions
- **Code review:** Security review for all changes

### 6. Code Quality

- **Use type hints:** Add type annotations
- **Format code:** Run black and isort
- **Lint regularly:** Use flake8 and mypy
- **Review standards:** Follow team standards

### 7. Deployment

- **Test before deploy:** Full test suite passes
- **Version properly:** Use semantic versioning
- **Document changes:** Maintain CHANGELOG
- **Rollback plan:** Always have rollback capability

---

## Advantages and Trade-offs

### Advantages

| Benefit | Description |
|---------|-------------|
| **Code Reuse** | Share code across all applications |
| **Consistency** | Unified tooling and standards |
| **Atomic Changes** | Change multiple apps/packages together |
| **Simplified Setup** | One repository to clone and setup |
| **Better Collaboration** | Easier to discover and share code |
| **Streamlined CI/CD** | Single pipeline for all projects |

### Trade-offs

| Challenge | Mitigation |
|-----------|-----------|
| **Repository Size** | Use .gitignore, clean caches regularly |
| **Build Times** | Conditional CI jobs, parallel testing |
| **Permissions** | Use CODEOWNERS for different apps |
| **Learning Curve** | Good documentation, clear structure |

---

## Future Enhancements

1. **Automated Releases:** Semantic versioning and automated releases
2. **Package Publishing:** Publish packages to PyPI
3. **Performance Monitoring:** Track build and test performance
4. **Documentation Site:** Automated documentation generation
5. **Code Generation:** Templates for new apps/packages
6. **Dependency Graph:** Visualize app/package dependencies

---

## References

- [Monorepo Tools](https://monorepo.tools/)
- [Python Packaging Guide](https://packaging.python.org/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Pytest Documentation](https://docs.pytest.org/)

---

**Last Updated:** 2025-11-15
**Maintained By:** Music Tools Team
**Status:** Production Ready
