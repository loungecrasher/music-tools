# Architecture Analysis Report

**Generated**: 2025-11-19
**Architecture Style**: Layered Monolith with Emerging Modular Design
**Overall Architecture Score**: 5.5/10

---

## Executive Summary

The codebase demonstrates a **transitional architecture** moving from a monolithic structure toward better separation of concerns. While some modules show good architectural patterns, significant inconsistencies and violations remain.

**Key Findings**:
- Mixed layering with violations at multiple points
- No clear service layer
- Direct database access from UI code
- Emerging package structure but incomplete
- Good module separation in some areas (library, scraping, tagging)
- Poor separation in others (menu, CLI)

---

## Current Architecture Overview

```
Music Tools Project
│
├── apps/music-tools/          # Main application
│   ├── menu.py                # Monolithic UI entry point
│   ├── setup_wizard.py        # Configuration setup
│   │
│   ├── music_tools_cli/       # Command-line interface
│   │   ├── cli.py             # CLI entry point
│   │   ├── commands/          # Command modules
│   │   └── services/          # Business logic (partial)
│   │
│   ├── src/                   # Core functionality
│   │   ├── library/           # Library management
│   │   ├── scraping/          # Web scraping
│   │   └── tagging/           # Metadata tagging
│   │
│   ├── legacy/                # Old scripts (tech debt)
│   └── tests/                 # Test suite (incomplete)
│
└── packages/common/           # Shared libraries
    └── music_tools_common/
        ├── api/               # API clients
        ├── auth/              # Authentication
        ├── config/            # Configuration
        ├── database/          # Data access
        └── utils/             # Utilities
```

---

## Separation of Concerns Analysis

### Score: 4/10

### Violations Found

#### 1. Presentation Layer Violations

**File**: `menu.py`
**Issue**: UI code contains business logic and data access

```python
# Lines 689-728 - UI code directly querying database
def show_database_info() -> None:
    with db:
        playlists = db.get_playlists()
        spotify_playlists = [p for p in playlists if p['service'] == 'spotify']
        # ... data manipulation in UI layer
```

**Violation**: Presentation layer directly accessing data layer
**Impact**: Cannot test business logic without UI
**Fix**: Move to service layer

---

#### 2. Business Logic in UI Layer

**File**: `menu.py`
**Lines**: 761-855

```python
def import_spotify_playlists() -> None:
    # UI rendering
    console.print(Panel(...))

    # Business logic (should be in service layer)
    with open(json_file, 'r') as f:
        data = json.load(f)
        total_playlists = calculate_total(data)  # Business logic

    # Data access (should be in repository)
    success, error = db.import_json_playlists(json_file, 'spotify')
```

**Violation**: Mixing all three concerns in single function

---

#### 3. Data Access Logic in Domain Objects

**File**: `src/library/indexer.py`
**Lines**: Throughout

```python
class LibraryIndexer:
    def __init__(self, db_path: str, console: Optional[Console] = None):
        self.db = LibraryDatabase(db_path)  # Direct DB dependency
        self.console = console               # UI dependency

    def index_library(self, ...):
        # Mix of business logic, data access, and UI
        self.console.print(...)              # UI call
        self.db.add_file(library_file)       # Data call
```

**Violation**: Domain service depends on both UI and data layers

---

### Proper Separation Examples

#### Positive Example: Config Manager

**File**: `packages/common/config/manager.py`

```python
class ConfigManager:
    # Pure data access - no UI, no complex business logic
    def load_config(self, service: str) -> Dict[str, Any]:
        # Just loads and returns
```

**Why Good**: Single responsibility, no layer violations

---

#### Positive Example: Library Models

**File**: `src/library/models.py`

```python
@dataclass
class LibraryFile:
    # Pure domain model - no dependencies
    file_path: str
    filename: str
    # ...
```

**Why Good**: Pure data model, no infrastructure concerns

---

## SOLID Principles Adherence

### Single Responsibility Principle: 3/10

**Violations**:
- `MusicBlogScraper`: 8+ responsibilities
- `Menu`: 10+ responsibilities
- `MusicTaggerCLI`: 6+ responsibilities

**Good Examples**:
- `LibraryFile`: Single data model
- `ConfigManager`: Single config responsibility
- `hash_utils.py`: Single utility purpose

---

### Open/Closed Principle: 5/10

**Violations**:
- No plugin architecture for new services
- Hard-coded service types throughout
- Must modify existing code to add new features

**Example Violation**:
```python
# menu.py - must modify to add new service
if service == 'spotify':
    # ...
elif service == 'deezer':
    # ...
# Can't add new service without modifying
```

**Good Example**:
```python
# models.py - uses Pydantic for extensibility
class BlogPost(BaseModel):
    # Can extend without modifying base
```

---

### Liskov Substitution Principle: 6/10

**Good**: Limited inheritance used, so less violation opportunity

**Violation Found**:
```python
# Different researcher classes not properly substitutable
ClaudeCodeResearcher vs AIResearcher
# Different interfaces, cannot swap
```

---

### Interface Segregation Principle: 4/10

**Violations**:
- `MusicBlogScraper`: Clients forced to depend on methods they don't use
- `Menu`: Single large interface instead of focused ones

**Should Be**:
```python
# Instead of one big scraper:
class PageFetcher:
    def get_page(url)

class LinkExtractor:
    def extract_links(soup)

class ContentFilter:
    def filter_by_genre(posts, genres)
```

---

### Dependency Inversion Principle: 3/10

**Major Violation**: High-level modules depend on low-level modules

**Example**:
```python
# High-level menu depends on low-level database
from music_tools_common.database import Database
db = Database()  # Direct dependency on concrete class

# Should be:
class IRepository(ABC):
    @abstractmethod
    def get_playlists(self): pass

class Menu:
    def __init__(self, repository: IRepository):
        self.repo = repository  # Depend on abstraction
```

**Impact**: Cannot mock, cannot swap implementations

---

## Design Patterns Analysis

### Patterns Used Correctly

#### 1. Factory Pattern (Partial)

**File**: `packages/common/database/manager.py`

```python
def get_database() -> Database:
    return db
```

**Note**: Good start but should use proper factory with DI

---

#### 2. Repository Pattern (Partial)

**File**: `src/library/database.py`

```python
class LibraryDatabase:
    def add_file(self, file: LibraryFile) -> int
    def get_file_by_path(self, path: str) -> Optional[LibraryFile]
```

**Note**: Good repository methods but no interface abstraction

---

#### 3. Strategy Pattern (Emerging)

**File**: `src/tagging/`

```python
# Different researcher strategies
ClaudeCodeResearcher
AIResearcher
```

**Note**: Pattern exists but not formalized with interface

---

#### 4. Builder Pattern (Good)

**File**: `src/scraping/models.py`

```python
class ScraperConfig(BaseModel):
    # Pydantic provides builder-like configuration
```

---

### Missing Patterns (Should Use)

#### 1. Service Layer Pattern

**Problem**: Business logic scattered across UI and data layers

**Should Have**:
```python
class PlaylistService:
    def __init__(self, repo: PlaylistRepository, logger: Logger):
        self.repo = repo
        self.logger = logger

    def import_playlists(self, file_path: str, service: str) -> ImportResult:
        # Centralized business logic
        # Validation
        # Coordination
        # Transaction management
```

---

#### 2. Command Pattern

**Problem**: CLI commands are functions, not objects

**Should Have**:
```python
class Command(ABC):
    @abstractmethod
    def execute(self): pass

class ImportPlaylistsCommand(Command):
    def __init__(self, service: PlaylistService, file_path: str):
        self.service = service
        self.file_path = file_path

    def execute(self):
        return self.service.import_playlists(self.file_path)
```

---

#### 3. Observer Pattern

**Problem**: Progress reporting mixed into business logic

**Should Have**:
```python
class ProgressObserver(ABC):
    @abstractmethod
    def update(self, progress: int): pass

class ConsoleProgressObserver(ProgressObserver):
    def update(self, progress: int):
        console.print(f"Progress: {progress}%")
```

---

#### 4. Adapter Pattern

**Problem**: Direct dependency on external libraries

**Should Have**:
```python
class HttpClient(ABC):
    @abstractmethod
    def get(self, url: str) -> Response: pass

class RequestsAdapter(HttpClient):
    def get(self, url: str) -> Response:
        return requests.get(url)
```

---

## Layer Architecture Evaluation

### Current Layer Issues

```
┌─────────────────────────────────────┐
│   Presentation Layer (UI)           │ ← Should only handle display
│   - menu.py                          │
│   - cli.py                           │
│   - Rich console calls               │
├─────────────────────────────────────┤
│                                      │
│   ❌ MISSING: Service/Business Layer│ ← Should coordinate business logic
│                                      │
├─────────────────────────────────────┤
│   Domain Layer                       │ ← Some good models
│   - models.py files                  │
│   - LibraryFile, BlogPost           │
├─────────────────────────────────────┤
│   Data Access Layer                  │ ← Good repository-like structure
│   - database.py                      │
│   - LibraryDatabase                  │
├─────────────────────────────────────┤
│   Infrastructure Layer               │ ← Partially implemented
│   - HTTP clients                     │
│   - File I/O                         │
│   - External services                │
└─────────────────────────────────────┘
```

### Violations

**Cross-Layer Access**:
1. **Presentation → Data** (❌ Bad)
   - `menu.py` → `database.py` directly
   - Lines: 689, 761, etc.

2. **Presentation → Infrastructure** (❌ Bad)
   - `menu.py` → `subprocess` calls
   - Lines: 241, 261

3. **Domain → Presentation** (❌ Bad)
   - `LibraryIndexer` → `Console` dependency
   - Line: 56

---

## Module Boundaries Analysis

### Well-Defined Boundaries

#### ✅ Scraping Module

**Path**: `src/scraping/`

**Structure**:
```
scraping/
├── __init__.py
├── models.py          # Domain models
├── config.py          # Configuration
├── music_scraper.py   # Main logic
├── error_handling.py  # Cross-cutting concern
└── cli_scraper.py     # CLI interface
```

**Why Good**:
- Clear responsibility (web scraping)
- Internal cohesion
- Exports well-defined interface

**Issues**:
- `music_scraper.py` is god object
- No clear service layer

---

#### ✅ Library Module

**Path**: `src/library/`

**Structure**:
```
library/
├── __init__.py
├── models.py            # Domain models
├── database.py          # Data access
├── indexer.py           # Business logic
├── duplicate_checker.py # Business logic
└── vetter.py            # Business logic
```

**Why Good**:
- Focused on library management
- Good separation of data and logic

**Issues**:
- Business logic classes directly depend on database
- UI dependencies in domain services

---

### Poorly-Defined Boundaries

#### ❌ Root Menu Module

**File**: `menu.py` (982 lines)

**Problems**:
- Single file handles multiple domains
- No clear module boundary
- Mixes all concerns

**Should Be**:
```
ui/
├── menu/
│   ├── menu_renderer.py
│   ├── menu_options.py
│   └── menu_navigation.py
├── dialogs/
│   ├── config_dialog.py
│   └── test_dialog.py
└── formatters/
    └── output_formatter.py
```

---

#### ❌ CLI Module

**Path**: `music_tools_cli/`

**Structure**:
```
music_tools_cli/
├── cli.py
├── commands/      # Command definitions
└── services/      # Business logic (partial)
```

**Problems**:
- `services/` not true service layer
- Mixed with command definitions
- No clear separation

**Should Be**:
```
application/
├── cli/
│   ├── commands/
│   └── parsers/
├── services/          # True business logic
│   ├── playlist_service.py
│   ├── library_service.py
│   └── scraper_service.py
└── repositories/      # Data access
    ├── playlist_repo.py
    └── track_repo.py
```

---

## Dependency Direction Analysis

### Current Dependency Graph

```
menu.py ─────────────┐
                     ├──> Database ──> SQLite
music_tools_cli ─────┘       │
                             │
                             ├──> music_tools_common
                             │
src/library ─────────────────┤
src/scraping ────────────────┤
src/tagging ─────────────────┘
```

**Problems**:
1. Multiple entry points depend on same low-level modules
2. No abstraction layer
3. Circular dependency risks

### Should Be (Clean Architecture)

```
┌──────────────────────────────────────────┐
│         Presentation Layer               │
│  (menu.py, cli.py, UI components)       │
└────────────┬─────────────────────────────┘
             │ depends on ↓
┌────────────┴─────────────────────────────┐
│         Application/Service Layer        │
│  (PlaylistService, LibraryService)      │
└────────────┬─────────────────────────────┘
             │ depends on ↓
┌────────────┴─────────────────────────────┐
│         Domain Layer                      │
│  (Models, Business Rules)                │
└────────────┬─────────────────────────────┘
             │ depends on ↓
┌────────────┴─────────────────────────────┐
│         Infrastructure Layer             │
│  (Repositories, External Services)       │
└──────────────────────────────────────────┘
```

---

## Package Cohesion Analysis

### music_tools_common Package

**Path**: `packages/common/music_tools_common/`

**Cohesion**: Medium (6/10)

**Structure**:
```
music_tools_common/
├── api/          # API clients (Spotify, Deezer)
├── auth/         # Authentication
├── cli/          # CLI utilities
├── config/       # Configuration
├── database/     # Data access
├── metadata/     # Metadata handling
└── utils/        # Utilities
```

**Strengths**:
- Logical grouping
- Reusable across apps
- Clear module purposes

**Weaknesses**:
- Too many responsibilities for "common"
- Some modules should be in domain layer
- CLI utilities in common package (wrong layer)

---

### Coupling Metrics (Estimated)

| Module Pair | Coupling | Direction | Issue |
|------------|----------|-----------|-------|
| menu ↔ database | HIGH | Tight | Direct dependency |
| cli ↔ services | MEDIUM | Loose | Some abstraction |
| scraper ↔ models | LOW | Loose | Good separation |
| indexer ↔ console | MEDIUM | Tight | UI in domain |
| All ↔ common | HIGH | Tight | God package |

---

## Recommended Architecture

### Target Architecture: Hexagonal (Ports & Adapters)

```
┌─────────────────────────────────────────────────────────┐
│                   Presentation Layer                    │
│  ┌───────────────────┐     ┌───────────────────┐       │
│  │   CLI Interface   │     │   Rich UI         │       │
│  └─────────┬─────────┘     └─────────┬─────────┘       │
│            │                          │                 │
└────────────┼──────────────────────────┼─────────────────┘
             │                          │
             │  Input Ports             │
             ↓                          ↓
┌─────────────────────────────────────────────────────────┐
│               Application Services                      │
│  ┌──────────────────┐  ┌──────────────────┐           │
│  │ PlaylistService  │  │  LibraryService  │           │
│  └────────┬─────────┘  └────────┬─────────┘           │
│           │                      │                      │
└───────────┼──────────────────────┼──────────────────────┘
            │                      │
            │  Domain Interfaces   │
            ↓                      ↓
┌─────────────────────────────────────────────────────────┐
│                   Domain Layer                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   Models     │  │  Validators  │  │  Exceptions  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
            ↑                      ↑
            │  Output Ports        │
            │                      │
┌───────────┼──────────────────────┼──────────────────────┐
│  Adapters │                      │                      │
│  ┌────────┴────────┐  ┌──────────┴────────┐           │
│  │  DB Repository  │  │  HTTP Client      │           │
│  └─────────────────┘  └───────────────────┘           │
└─────────────────────────────────────────────────────────┘
```

### Implementation Steps

1. **Create Port Interfaces** (Week 1-2)
   ```python
   # ports/repositories.py
   class PlaylistRepository(ABC):
       @abstractmethod
       def save(self, playlist: Playlist) -> None: pass

       @abstractmethod
       def find_by_id(self, id: str) -> Optional[Playlist]: pass
   ```

2. **Implement Application Services** (Week 2-3)
   ```python
   # services/playlist_service.py
   class PlaylistService:
       def __init__(self, repo: PlaylistRepository):
           self.repo = repo

       def import_from_file(self, path: str) -> ImportResult:
           # Business logic here
   ```

3. **Create Adapters** (Week 3-4)
   ```python
   # adapters/sqlite_playlist_repo.py
   class SQLitePlaylistRepository(PlaylistRepository):
       def save(self, playlist: Playlist) -> None:
           # SQLite-specific implementation
   ```

4. **Refactor UI** (Week 4-5)
   ```python
   # ui/menu.py
   class Menu:
       def __init__(self, playlist_service: PlaylistService):
           self.service = playlist_service

       def import_playlists(self):
           result = self.service.import_from_file(path)
           self.display_result(result)
   ```

---

## Architecture Recommendations

### Immediate (This Sprint)

1. **Create Service Layer**
   - Extract business logic from UI
   - Create service classes for each domain

2. **Define Repository Interfaces**
   - Abstract data access
   - Enable testing with mocks

3. **Remove Cross-Layer Dependencies**
   - UI should not import database
   - Domain should not import UI

### Short-term (Next Month)

4. **Implement Hexagonal Architecture**
   - Define ports (interfaces)
   - Create adapters for external systems
   - Dependency injection

5. **Extract menu.py Into Modules**
   - Separate UI rendering
   - Separate business coordination
   - Separate configuration

### Long-term (Next Quarter)

6. **Microservices Consideration**
   - Scraping service
   - Tagging service
   - Library management service
   - (if scale requires)

7. **Event-Driven Architecture**
   - Decouple components
   - Use message bus for communication

---

## Architecture Maturity Score

| Aspect | Score | Notes |
|--------|-------|-------|
| Layer Separation | 3/10 | Major violations |
| SOLID Adherence | 4/10 | SRP violations common |
| Design Patterns | 5/10 | Some good, many missing |
| Module Boundaries | 6/10 | Good in places, poor overall |
| Dependency Management | 3/10 | Tight coupling throughout |
| Testability | 4/10 | Hard to test due to coupling |
| **Overall** | **4.2/10** | **Needs significant refactoring** |

---

## Positive Architectural Findings

1. **Package Structure**: Good organization into `library`, `scraping`, `tagging`
2. **Models Separation**: Domain models are generally well-defined
3. **Pydantic Usage**: Good data validation in scraping module
4. **Config Abstraction**: ConfigManager is well-designed
5. **Recent Refactoring**: `cli.py` shows architectural improvement

---

## Critical Architectural Risks

1. **Tight Coupling**: Cannot swap implementations
2. **No Service Layer**: Business logic scattered
3. **Direct Dependencies**: Hard to test, hard to maintain
4. **God Objects**: Violate multiple principles
5. **Mixed Concerns**: All layers tangled together

**Estimated Refactoring Effort**: 60-80 hours for proper architecture
