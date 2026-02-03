# Anti-Patterns Detection Report

**Generated**: 2025-11-19
**Analysis Scope**: Complete codebase
**Anti-Patterns Identified**: 23

---

## Severity Distribution

| Severity | Count | Impact |
|----------|-------|--------|
| Critical | 6 | System-wide maintainability issues |
| High | 9 | Module-level problems |
| Medium | 8 | Local concerns |

---

## 1. God Objects (Critical)

### 1.1 MusicBlogScraper Class

**File**: `src/scraping/music_scraper.py`
**Lines**: 1,009
**Methods**: 30+

**Problem**:
- Single class handles scraping, parsing, filtering, date extraction, link quality detection, genre extraction, and file I/O
- Violates Single Responsibility Principle
- Difficult to test individual components
- High coupling between concerns

**Evidence**:
```python
class MusicBlogScraper:
    def get_page_content()          # HTTP concern
    def find_blog_posts()            # Navigation concern
    def extract_genre_keywords()     # Content parsing
    def extract_download_links()     # Link extraction
    def filter_posts_by_genre()      # Business logic
    def extract_post_date()          # Date parsing
    def is_flac_link()               # Quality detection
    def save_results()               # File I/O
    # + 20 more methods
```

**Impact**: High maintenance cost, testing difficulty
**Fix Complexity**: 15-20 hours

---

### 1.2 Menu Class God Object

**File**: `menu.py`
**Lines**: 982
**Methods**: 25+

**Problem**:
- Handles UI rendering, Spotify integration, Deezer integration, database management, configuration, and testing
- Mixes presentation, business, and data layers
- 50+ line methods with multiple responsibilities

**Evidence**:
```python
class Menu:
    def display()                    # UI
    def configure_spotify()          # Configuration
    def configure_deezer()           # Configuration
    def test_spotify_connection()   # Integration
    def test_deezer_connection()    # Integration
    def show_database_info()        # Data access
    def import_spotify_playlists()  # Business logic
    # Handles 8+ distinct responsibilities
```

**Impact**: Extremely difficult to maintain and test
**Fix Complexity**: 20-25 hours

---

### 1.3 MusicTaggerCLI God Object

**File**: `src/tagging/cli.py`
**Lines**: 1,544
**Methods**: 40+

**Problem**:
- Despite recent refactoring, still monolithic
- Helper classes created but kept in same file
- Should be split into separate modules

**Note**: Partially mitigated by helper classes:
- `ConfigurationWizard`
- `LibraryPathManager`
- `MusicLibraryProcessor`
- `DiagnosticsRunner`

**Impact**: File too large to review effectively
**Fix Complexity**: 10-12 hours (extract classes to modules)

---

## 2. Tight Coupling (High)

### 2.1 Direct Database Access in UI Code

**Files**: Multiple
**Severity**: High

**Problem**:
```python
# In menu.py (lines 689-728)
with db:
    playlists = db.get_playlists()  # Direct DB access in UI layer
    tracks = db.get_tracks()
```

**Issue**: No abstraction layer between UI and data
**Fix**: Implement repository pattern

---

### 2.2 Hardcoded Service Dependencies

**File**: `menu.py`
**Lines**: 31-57

**Problem**:
```python
try:
    from music_tools_common.auth import get_spotify_client, get_deezer_client
    from music_tools_common.config import config_manager
    # Direct coupling to specific implementations
except ImportError as e:
    print(f"Error: Core modules not found")
    sys.exit(1)
```

**Issue**: Cannot swap implementations or mock for testing
**Fix**: Dependency injection

---

## 3. Magic Numbers and Strings (High)

### 3.1 Scattered Configuration Constants

**Files**: Multiple
**Severity**: High

**Examples**:
```python
# menu.py:228
env['SPOTIPY_REDIRECT_URI'] = 'http://localhost:8888/callback'  # Magic string

# music_scraper.py:141
estimated_pages = max(10, min(100, days_to_scan // 2))  # Magic numbers

# cli.py:1239
timeout=600,  # Magic number - 10 minutes

# database.py:88
timeout=30.0,  # Magic number
```

**Impact**: Difficult to maintain, easy to create bugs
**Count**: 50+ instances across codebase

**Fix Required**:
```python
# Constants module needed
DEFAULT_TIMEOUT_SECONDS = 30.0
MAX_PAGINATION_PAGES = 100
DEFAULT_BATCH_SIZE = 10
SPOTIFY_REDIRECT_URI = 'http://localhost:8888/callback'
```

---

## 4. Callback Hell / Deep Nesting (Medium)

### 4.1 Nested Try-Except Blocks

**File**: `menu.py`
**Lines**: 202-303

**Problem**:
```python
def run_tool(script_path: str) -> None:
    try:
        if not os.path.isfile(script_path):
            console.print(f"\n[bold red]Tool script not found...")
            return

        if "Spotify Script" in script_path:
            spotify_config = get_config('spotify')
            if spotify_config:
                env['SPOTIPY_CLIENT_ID'] = spotify_config.get('client_id', '')

        if ("Library Comparison" in script_path or ...):
            console.print(f"\n[bold green]Running...")
            process = subprocess.Popen(...)
        else:
            with console.status(...):
                process = subprocess.Popen(...)
                stdout, stderr = process.communicate()

        if return_code == 0:
            console.print(...)
        else:
            console.print(...)
    except subprocess.CalledProcessError as e:
        console.print(...)
    except KeyboardInterrupt:
        console.print(...)
```

**Issues**:
- 4-5 levels of nesting
- Complex conditional logic
- Multiple responsibilities

**Cyclomatic Complexity**: Estimated 15+

---

### 4.2 Deep Menu Display Logic

**File**: `menu.py`
**Lines**: 148-200

**Problem**:
```python
def display(self) -> None:
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')

        table = Table(...)
        table.add_column(...)

        for i, option in enumerate(self.options, 1):
            if option.description:
                table.add_row(...)
            else:
                table.add_row(...)

        if self.exit_option:
            table.add_row(...)

        console.print(Panel(...))

        try:
            choice = Prompt.ask(...)

            if choice == '0' and self.exit_option:
                self.exit_option.action()
                return

            try:
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(self.options):
                    self.options[choice_idx].action()
                else:
                    console.print(...)
            except ValueError:
                console.print(...)
        except KeyboardInterrupt:
            console.print(...)
```

**Issues**: 4 levels of nesting, mixed concerns

---

## 5. Feature Envy (Medium)

### 5.1 Menu Accessing Database Internals

**File**: `menu.py`
**Lines**: 689-759

**Problem**:
```python
def show_database_info() -> None:
    with db:
        playlists = db.get_playlists()
        spotify_playlists = [p for p in playlists if p['service'] == 'spotify']
        deezer_playlists = [p for p in playlists if p['service'] == 'deezer']

        tracks = db.get_tracks()
        spotify_tracks = [t for t in tracks if t['service'] == 'spotify']
        deezer_tracks = [t for t in tracks if t['service'] == 'deezer']
```

**Issue**: Menu knows too much about database structure
**Fix**: Move this logic to database/repository layer

---

## 6. Inappropriate Intimacy (Medium)

### 6.1 Direct File System Access in Multiple Layers

**Files**: `menu.py`, `cli.py`, `indexer.py`

**Problem**:
- UI code directly accesses file system
- Business logic directly accesses file system
- No abstraction layer

**Example**:
```python
# In menu.py (UI layer):
if os.path.exists(default_path):
    use_default = Confirm.ask("Use this file?", default=True)
```

**Issue**: Cannot test without real file system

---

## 7. God Functions (High)

### 7.1 filter_posts_by_genre Method

**File**: `music_scraper.py`
**Lines**: 591-691 (100 lines)
**Cyclomatic Complexity**: ~18

**Problem**:
- Filters posts
- Extracts metadata
- Validates data
- Converts formats
- Multiple nested loops and conditions

---

### 7.2 _process_music_library (RESOLVED)

**File**: `cli.py`
**Previous Lines**: 326
**Status**: Successfully refactored into 10 methods

**Note**: This is a **positive finding** showing proper refactoring

---

## 8. Dead Code (Medium)

### 8.1 Backup File in Source Tree

**File**: `src/tagging/cli_original_backup_20251119.py`
**Lines**: 1,285
**Severity**: Medium

**Problem**:
- Complete duplicate of `cli.py` before refactoring
- Should be in version control history, not source tree
- Increases codebase size by 5%

**Action**: DELETE immediately

---

### 8.2 Unused Imports

**Multiple Files**

**Examples**:
```python
# Common pattern found:
from typing import Optional, List, Dict, Any
# But only using List and Dict
```

**Impact**: Code smell, indicates incomplete refactoring

---

## 9. Primitive Obsession (Medium)

### 9.1 String-Based Service Identifiers

**Files**: Multiple
**Severity**: Medium

**Problem**:
```python
service = 'spotify'  # String primitive
service = 'deezer'   # String primitive

# Should be:
class ServiceType(Enum):
    SPOTIFY = "spotify"
    DEEZER = "deezer"
```

**Impact**: Typo-prone, no type safety

---

### 9.2 Dictionary Passing Instead of Objects

**Files**: `music_scraper.py`, `database.py`

**Problem**:
```python
def add_playlist(self, playlist: Dict[str, Any], service: str):
    # Passing dict instead of Playlist object
```

**Fix**: Create proper domain models

---

## 10. Long Parameter Lists (Medium)

### 10.1 MusicLibraryProcessor Constructor

**File**: `cli.py`
**Line**: 414

**Problem**:
```python
def __init__(self, scanner, metadata_handler, ai_researcher,
             cache_manager, config, verbose=False):
    # 6 parameters
```

**Fix**: Use dependency injection container or builder pattern

---

## 11. Shotgun Surgery (High)

### 11.1 Configuration Changes

**Impact**: High

**Problem**:
- Changing how configuration works requires editing:
  - `menu.py`
  - `cli.py`
  - `setup_wizard.py`
  - `packages/common/config/manager.py`
  - Multiple service files

**Count**: 10+ files need changes for single feature

---

## 12. Duplicate Code (Critical)

### 12.1 Error Handling Pattern

**Occurrences**: 40+

**Pattern**:
```python
try:
    # operation
except Exception as e:
    logger.error(f"Error: {e}")
    console.print(f"[red]Error: {e}[/red]")
    return None/False
```

**Fix**: Create error handling decorator or utility

---

### 12.2 Progress Bar Creation

**Occurrences**: 10+

**Pattern**:
```python
with Progress(
    SpinnerColumn(),
    TextColumn("[progress.description]{task.description}"),
    BarColumn(),
    TaskProgressColumn(),
    console=console
) as progress:
    task = progress.add_task(...)
```

**Fix**: Extract to utility function

---

### 12.3 Database Connection Pattern

**Occurrences**: 5+

**Pattern**:
```python
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
```

**Fix**: Use context manager or connection factory

---

## 13. Missing Abstraction (High)

### 13.1 No Repository Pattern

**Files**: `menu.py`, multiple services

**Problem**:
- Direct database queries in UI code
- No abstraction between data and business logic
- Difficult to swap data sources

**Fix**: Implement repository interfaces

---

### 13.2 No Service Layer

**Problem**:
- Business logic scattered across UI, data, and util layers
- No clear place for complex operations

**Fix**: Create service layer between UI and data

---

## 14. Copy-Paste Programming (High)

### 14.1 Similar CLI Command Patterns

**Files**: `music_tools_cli/commands/*.py`

**Pattern**: Each command file has similar structure but no shared base

**Example**:
```python
# Pattern repeated in spotify.py, deezer.py, library.py:
app = typer.Typer(help="...")

@app.command("action")
def action_command():
    """Docstring"""
    # Setup
    # Validation
    # Execute
    # Display results
```

**Fix**: Create base command class with template method

---

## 15. Magic Constants in Logic (High)

### 15.1 Hardcoded Limits

**File**: `music_scraper.py`

**Problem**:
```python
# Line 155
estimated_pages = max(10, min(100, days_to_scan // 2))

# Line 195
if pages_without_target_content >= 3:  # Magic number

# Line 261
if re.search(r'\d{4}', url):  # Magic regex
```

**Fix**: Extract to named constants with documentation

---

## 16. Mixed Concerns in Modules (Medium)

### 16.1 menu.py Contains Everything

**Problem**: Single file contains:
- Menu UI classes
- Configuration functions
- Database operations
- Service testing
- File running
- Welcome screen
- Main application loop

**Fix**: Split into modules:
- `ui/menu_display.py`
- `config/setup.py`
- `services/service_test.py`
- etc.

---

## 17. Inconsistent Error Handling (Medium)

### 17.1 Mix of Exception Types

**Problem**:
```python
# Some functions:
return None on error

# Other functions:
raise Exception()

# Others:
return (False, error_message)

# Others:
return Result object
```

**Fix**: Standardize on single error handling strategy

---

## 18. Test Smells (Medium)

### 18.1 Incomplete Test Coverage

**File**: `tests/database/`

**Problem**:
- Tests exist but only for database layer
- No tests for:
  - Menu system
  - CLI commands
  - Scraping logic
  - Integration tests

---

### 18.2 Missing Test Fixtures

**File**: `tests/database/conftest.py`

**Problem**:
- Minimal fixture setup
- Each test creates own test data
- Lots of duplication in test files

---

## 19. Leaky Abstractions (Medium)

### 19.1 Rich Console Leaking Everywhere

**Files**: Multiple

**Problem**:
```python
# Every module imports and uses Rich directly
from rich.console import Console
console = Console()
console.print("[red]Error[/red]")
```

**Issue**:
- Cannot change UI library without touching every file
- Difficult to test output

**Fix**: Create output abstraction layer

---

## 20. Anemic Domain Model (Medium)

### 20.1 Data Classes Without Behavior

**File**: `src/library/models.py`

**Problem**:
```python
@dataclass
class LibraryFile:
    file_path: str
    filename: str
    artist: Optional[str]
    # ... just data, no behavior
```

**Issue**: All logic in separate service classes

**Note**: This is somewhat acceptable with proper service layer, but mixing with other anti-patterns

---

## 21. Hard-Coded Paths (Medium)

### 21.1 Hardcoded Music Directories

**File**: `cli.py`
**Lines**: 350-358

**Problem**:
```python
common_dirs = [
    "~/Music",
    "~/Documents/Music",
    "/Users/patrickoliver/Track Library",  # Personal path!
    "/Users/patrickoliver/Music Library",  # Personal path!
]
```

**Issue**: Contains developer's personal paths in source code

**Fix**: Move to configuration or user settings

---

## 22. Global State (Low-Medium)

### 22.1 Global Database Instance

**File**: `packages/common/database/manager.py`

**Problem**:
```python
# Line 660
db = Database()

# Line 662
def get_database() -> Database:
    return db
```

**Issue**: Global mutable state, difficult to test in isolation

---

### 22.2 Global Config Manager

**File**: `packages/common/config/manager.py`

**Problem**:
```python
# Line 232
config_manager = ConfigManager()
```

**Issue**: Singleton pattern, but as global variable

---

## 23. String Concatenation for Paths (Low)

### 23.1 os.path.join vs Pathlib

**Files**: Multiple

**Problem**: Inconsistent use of path manipulation
```python
# Some files use:
os.path.join(dir, file)

# Others use:
Path(dir) / file

# Mix of both in same file
```

**Fix**: Standardize on `pathlib.Path` throughout

---

## Summary Statistics

| Anti-Pattern Category | Count | Severity |
|----------------------|-------|----------|
| God Objects | 3 | Critical |
| Tight Coupling | 2 | High |
| Magic Numbers | 50+ | High |
| Callback Hell | 2 | Medium |
| Feature Envy | 1 | Medium |
| Duplicate Code | 3 patterns | Critical |
| Missing Abstractions | 2 | High |
| Inconsistent Patterns | 4 | Medium |
| Dead Code | 2 | Medium |
| Hard-coded Values | 2 | Medium |
| Global State | 2 | Low-Medium |

---

## Refactoring Priority

### Critical (Fix Immediately)
1. Remove backup file (`cli_original_backup_20251119.py`)
2. Extract duplicate error handling pattern
3. Extract duplicate progress bar pattern
4. Remove hardcoded personal paths

### High (Next Sprint)
5. Refactor `MusicBlogScraper` god object
6. Refactor `Menu` god object
7. Extract magic numbers to constants
8. Implement repository pattern

### Medium (Next Month)
9. Extract `cli.py` helper classes to modules
10. Standardize error handling
11. Create service layer
12. Fix shotgun surgery in configuration

### Low (Long-term)
13. Standardize on pathlib throughout
14. Fix global state patterns
15. Create proper domain models
