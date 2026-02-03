# Duplicate Detection Enhancement - Implementation Plan

**Date:** 2025-11-19
**Goal:** Build professional library indexing and import vetting system
**Estimated Time:** 17 hours (Phases 1-3)
**Status:** Starting Implementation

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Music Tools Suite                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐      ┌──────────────────┐           │
│  │  Library Indexer │──────│  SQLite Database │           │
│  │                  │      │  (library_index) │           │
│  └──────────────────┘      └──────────────────┘           │
│           │                                                 │
│           │                                                 │
│           ▼                                                 │
│  ┌──────────────────┐      ┌──────────────────┐           │
│  │  Import Vetter   │──────│  Duplicate       │           │
│  │                  │      │  Checker         │           │
│  └──────────────────┘      └──────────────────┘           │
│           │                                                 │
│           │                                                 │
│           ▼                                                 │
│  ┌──────────────────┐                                      │
│  │  CLI Commands    │                                      │
│  │  - library index │                                      │
│  │  - library vet   │                                      │
│  └──────────────────┘                                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Module Structure

```
apps/music-tools/
├── src/
│   └── library/                        # NEW
│       ├── __init__.py
│       ├── indexer.py                  # Phase 1
│       ├── vetter.py                   # Phase 2
│       ├── duplicate_checker.py        # Phase 2
│       ├── models.py                   # Data models
│       └── database.py                 # Database management
│
├── music_tools_cli/
│   └── commands/
│       └── library.py                  # Phase 3 - Enhanced
│
└── tests/
    └── library/                        # Tests
        ├── test_indexer.py
        ├── test_vetter.py
        └── test_duplicate_checker.py
```

---

## Phase 1: Library Indexer (6 hours)

### Files to Create:

1. **`src/library/models.py`** - Data models
2. **`src/library/database.py`** - Database management
3. **`src/library/indexer.py`** - Main indexer logic

### Key Classes:

```python
# models.py
@dataclass
class LibraryFile:
    file_path: str
    filename: str
    artist: Optional[str]
    title: Optional[str]
    album: Optional[str]
    year: Optional[int]
    duration: Optional[float]
    file_format: str
    file_size: int
    metadata_hash: str
    file_content_hash: str
    indexed_at: datetime
    file_mtime: datetime

# database.py
class LibraryDatabase:
    def __init__(self, db_path: str)
    def create_tables(self)
    def add_file(self, file: LibraryFile)
    def get_file_by_path(self, path: str)
    def get_file_by_metadata_hash(self, hash: str)
    def get_file_by_content_hash(self, hash: str)
    def get_all_files(self)
    def update_file(self, file: LibraryFile)
    def mark_inactive(self, path: str)
    def get_statistics(self)

# indexer.py
class LibraryIndexer:
    def __init__(self, db_path: str)
    def index_library(self, library_path: str, rescan: bool = False)
    def _scan_directory(self, path: str)
    def _extract_metadata(self, file_path: str) -> LibraryFile
    def _calculate_hashes(self, file_path: str, metadata: dict)
    def _is_file_changed(self, file_path: str, db_record)
    def verify_library(self, library_path: str)
    def get_statistics(self)
```

---

## Phase 2: Import Vetter (8 hours)

### Files to Create:

1. **`src/library/duplicate_checker.py`** - Duplicate detection logic
2. **`src/library/vetter.py`** - Import vetting workflow

### Key Classes:

```python
# duplicate_checker.py
@dataclass
class DuplicateResult:
    is_duplicate: bool
    confidence: float
    match_type: str  # exact_metadata/fuzzy_metadata/exact_file/acoustic
    matched_file: Optional[LibraryFile]
    all_matches: List[Tuple[LibraryFile, float]]

class DuplicateChecker:
    def __init__(self, library_db: LibraryDatabase)
    def check_file(self, file_path: str) -> DuplicateResult
    def _check_metadata_hash(self, file: LibraryFile)
    def _check_fuzzy_metadata(self, file: LibraryFile, threshold: float)
    def _check_file_hash(self, file: LibraryFile)
    def _normalize_string(self, text: str) -> str
    def _calculate_similarity(self, str1: str, str2: str) -> float

# vetter.py
@dataclass
class VettingReport:
    total_files: int
    duplicates: List[Tuple[str, DuplicateResult]]
    new_songs: List[str]
    uncertain: List[Tuple[str, DuplicateResult]]

    def display(self)
    def export_new_songs(self, output_file: str)
    def export_duplicates(self, output_file: str)

class ImportVetter:
    def __init__(self, library_db: LibraryDatabase)
    def vet_folder(self, import_folder: str, threshold: float = 0.8)
    def _scan_import_folder(self, folder: str)
    def _categorize_results(self, results: List[DuplicateResult])
    def generate_report(self) -> VettingReport
```

---

## Phase 3: CLI Integration (3 hours)

### Enhanced Commands:

```python
# music_tools_cli/commands/library.py

@app.command("index")
def index_library(
    library_path: Path = typer.Option(..., "--path", "-p"),
    db_path: Path = typer.Option(None, "--db"),
    rescan: bool = typer.Option(False, "--rescan"),
    incremental: bool = typer.Option(True, "--incremental")
):
    """Index your main music library for duplicate detection."""

@app.command("vet")
def vet_import(
    import_folder: Path = typer.Option(..., "--folder", "-f"),
    library_db: Path = typer.Option(None, "--library-db"),
    threshold: float = typer.Option(0.8, "--threshold", "-t"),
    auto_skip: bool = typer.Option(False, "--auto-skip"),
    export_new: bool = typer.Option(True, "--export-new")
):
    """Vet import folder against indexed library."""

@app.command("verify")
def verify_library(
    library_path: Path = typer.Option(..., "--path", "-p"),
    db_path: Path = typer.Option(None, "--db"),
    check_missing: bool = typer.Option(True),
    check_moved: bool = typer.Option(True)
):
    """Verify library index is up-to-date."""

@app.command("stats")
def library_stats(
    db_path: Path = typer.Option(None, "--db")
):
    """Show library index statistics."""
```

---

## Database Schema

```sql
CREATE TABLE library_index (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- File information
    file_path TEXT UNIQUE NOT NULL,
    filename TEXT NOT NULL,

    -- Metadata
    artist TEXT,
    title TEXT,
    album TEXT,
    year INTEGER,
    duration REAL,
    file_format TEXT NOT NULL,  -- mp3, flac, m4a, wav
    file_size INTEGER NOT NULL,

    -- Hashing for duplicate detection
    metadata_hash TEXT NOT NULL,      -- MD5 of normalized artist|title
    file_content_hash TEXT NOT NULL,  -- MD5 of file bytes (first 64KB + last 64KB for speed)

    -- Timestamps
    indexed_at TEXT NOT NULL,
    file_mtime TEXT NOT NULL,
    last_verified TEXT,

    -- Status
    is_active INTEGER DEFAULT 1,

    -- Indexes for fast lookups
    UNIQUE(file_path)
);

CREATE INDEX idx_metadata_hash ON library_index(metadata_hash);
CREATE INDEX idx_content_hash ON library_index(file_content_hash);
CREATE INDEX idx_artist_title ON library_index(artist, title);
CREATE INDEX idx_is_active ON library_index(is_active);
CREATE INDEX idx_file_format ON library_index(file_format);

-- Statistics table
CREATE TABLE library_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    total_files INTEGER,
    total_size INTEGER,
    formats_breakdown TEXT,  -- JSON
    last_index_time TEXT,
    index_duration REAL,
    created_at TEXT
);

-- Vetting history
CREATE TABLE vetting_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    import_folder TEXT NOT NULL,
    total_files INTEGER,
    duplicates_found INTEGER,
    new_songs INTEGER,
    uncertain_matches INTEGER,
    threshold_used REAL,
    vetted_at TEXT NOT NULL
);
```

---

## Implementation Checklist

### Phase 1: Library Indexer
- [ ] Create `src/library/` directory
- [ ] Implement `models.py` with LibraryFile dataclass
- [ ] Implement `database.py` with LibraryDatabase class
- [ ] Implement `indexer.py` with LibraryIndexer class
- [ ] Add hash calculation (metadata + content)
- [ ] Add incremental indexing logic
- [ ] Add progress tracking with Rich
- [ ] Write unit tests for indexer
- [ ] Test with sample library

### Phase 2: Import Vetter
- [ ] Implement `duplicate_checker.py`
- [ ] Add exact metadata matching
- [ ] Add fuzzy metadata matching (from library_comparison.py)
- [ ] Add file content hash matching
- [ ] Implement `vetter.py` with ImportVetter class
- [ ] Add VettingReport with Rich display
- [ ] Add export functionality
- [ ] Write unit tests for vetter
- [ ] Integration test: index + vet workflow

### Phase 3: CLI Integration
- [ ] Update `music_tools_cli/commands/library.py`
- [ ] Add `library index` command
- [ ] Add `library vet` command
- [ ] Add `library verify` command
- [ ] Add `library stats` command
- [ ] Add command-line help text
- [ ] Test all commands
- [ ] Create usage documentation

### Testing & Documentation
- [ ] Write comprehensive tests
- [ ] Create usage examples
- [ ] Update README
- [ ] Create migration guide from old tools
- [ ] Performance benchmarks

---

## Success Criteria

### Performance:
- [ ] Initial index: < 2 seconds per 1000 files
- [ ] Incremental index: < 0.5 seconds per 1000 files (unchanged)
- [ ] Duplicate check: < 50ms per file
- [ ] Database queries: < 10ms

### Accuracy:
- [ ] 100% exact duplicate detection
- [ ] 95%+ fuzzy duplicate detection (with 0.8 threshold)
- [ ] < 1% false positives

### Usability:
- [ ] One-command indexing
- [ ] One-command vetting
- [ ] Clear, actionable reports
- [ ] Export lists for automation

---

## Timeline

**Day 1 (6 hours)**: Phase 1 - Library Indexer
- Hours 1-2: Models and database setup
- Hours 3-4: Indexer logic and hashing
- Hours 5-6: Testing and optimization

**Day 2 (8 hours)**: Phase 2 - Import Vetter
- Hours 1-3: Duplicate checker implementation
- Hours 4-6: Vetter workflow and reporting
- Hours 7-8: Testing and refinement

**Day 3 (3 hours)**: Phase 3 - CLI Integration
- Hours 1-2: Command implementation
- Hour 3: Testing and documentation

---

## Dependencies

**Already Available:**
- mutagen (metadata extraction)
- hashlib (hashing)
- sqlite3 (database)
- rich (UI)
- typer (CLI)
- pathlib (file operations)

**May Need:**
- difflib (fuzzy matching - standard library)

**Future Optional:**
- chromaprint (audio fingerprinting)
- librosa (audio analysis)

---

*Ready to implement - Starting with Phase 1*
