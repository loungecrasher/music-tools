# Music Library Duplicate Detection - Analysis & Enhancement Plan

**Date:** 2025-11-19
**Use Case:** Professional Music Curator - Import Vetting Workflow
**Requirement:** Check if new music already exists in main library before import

---

## 1. ✅ EXISTING FEATURES ANALYSIS

### Current Duplicate Detection Capabilities:

Your app **DOES have duplicate detection features**, but they're **scattered across legacy tools** and **not optimized for your specific workflow**.

### A. Legacy Tools (Standalone)

#### **Tool 1: Duplicate Remover**
**Location**: `legacy/Library Comparison/duplicate_remover.py`

**What it does:**
- Scans a **single directory** for duplicates
- Compares based on **artist + title metadata**
- Preference: FLAC > MP3 (keeps higher quality)
- Interactive deletion with dry-run mode

**Matching Method:**
- Exact metadata match: `artist|title` as unique key
- No fuzzy matching
- Uses mutagen to read ID3/Vorbis tags

**Limitations for your workflow:**
- ❌ Only scans ONE directory at a time
- ❌ No database - doesn't remember main library
- ❌ Can't compare "new folder" vs "main library"
- ❌ No persistent tracking

---

#### **Tool 2: Library Comparison**
**Location**: `legacy/Library Comparison/library_comparison.py`

**What it does:**
- Compares **two separate directories** (Library A vs Library B)
- Finds duplicates **across** libraries
- Supports **fuzzy matching** (80% similarity threshold)
- Can delete duplicates from Library B while preserving Library A

**Matching Methods:**
1. **Exact Match**: Case-insensitive `artist|title`
2. **Fuzzy Match**: SequenceMatcher with 80% similarity
   - Normalizes strings (removes "remastered", "feat", etc.)
   - Calculates similarity for both artist AND title
   - Combined score must be ≥ 0.8

**Strengths for your workflow:**
- ✅ Compares new folder vs main library
- ✅ Fuzzy matching catches variations
- ✅ Preserves main library by default
- ✅ Interactive confirmation

**Limitations for your workflow:**
- ❌ No database - must scan both directories every time
- ❌ Slow for large libraries (thousands of files)
- ❌ No persistent "already checked" tracking
- ❌ No audio fingerprinting (only metadata)

---

### B. Modern File Tracking (Integrated into Tagging App)

#### **Tool 3: Batch Processor with SQLite Database**
**Location**: `src/tagging/processor.py`

**What it does:**
- Maintains **SQLite database** of all processed files
- Tracks files by **MD5 hash** of `path:size:mtime`
- Prevents reprocessing of unchanged files
- Resume capability for interrupted processing

**Database Schema:**
```sql
CREATE TABLE file_records (
    id INTEGER PRIMARY KEY,
    file_path TEXT UNIQUE,
    file_hash TEXT,  -- MD5 of path:size:mtime
    artist TEXT,
    country TEXT,    -- From AI tagging
    processed_at TEXT,
    status TEXT,     -- pending/processed/error/skipped
    ...
)
```

**Strengths for your workflow:**
- ✅ SQLite database for persistence
- ✅ Fast lookups with indexes
- ✅ Tracks file changes
- ✅ Already integrated into main app

**Limitations for your workflow:**
- ❌ Database tracks **processed files** for tagging, not duplicates
- ❌ Hash is based on path/size/mtime, not content
- ❌ No duplicate detection logic built-in
- ❌ Not designed for "is this in my library?" queries

---

## 2. ❌ WHAT'S MISSING FOR YOUR WORKFLOW

### Your Ideal Workflow:
```
1. You have a "main library" with 50,000+ vetted songs
2. You download a new folder with 2,000 songs to evaluate
3. You want to know: "Which of these 2,000 are already in my library?"
4. For duplicates: Skip them immediately, don't waste time reviewing
5. For new songs: Focus your curation effort here
```

### Gaps in Current Implementation:

| Requirement | Existing Tool | Gap |
|-------------|---------------|-----|
| **Fast duplicate checking** | Library Comparison | ⚠️ Slow - rescans everything |
| **Persistent main library database** | None | ❌ Missing |
| **Batch import vetting** | None | ❌ Missing |
| **Audio fingerprinting** | None | ❌ Missing |
| **Content-based hashing** | None | ❌ Missing |
| **Automatic duplicate flagging** | Library Comparison | ⚠️ Manual only |
| **Import workflow integration** | None | ❌ Missing |

---

## 3. 🎯 ENHANCEMENT PLAN

### Recommended Approach: **Build on Existing Foundation**

Use the strengths of both legacy tools + modern database infrastructure:
- **Library Comparison** fuzzy matching logic ✅
- **Batch Processor** SQLite database ✅
- **New:** Library Indexing System
- **New:** Import Vetting Workflow

---

### **Phase 1: Create Main Library Index** (4-6 hours)

**Goal**: Build a persistent database of your main library

#### New Module: `library_indexer.py`

**Features**:
1. **Index Main Library**
   - Scan designated "main library" directories
   - Extract metadata: artist, title, album, year, duration
   - Calculate **multiple hashes**:
     - Metadata hash (artist|title)
     - File content hash (MD5 of entire file)
     - Optional: Audio fingerprint (for exact duplicates with different metadata)
   - Store in SQLite database

2. **Database Schema Extension**:
```sql
CREATE TABLE library_index (
    id INTEGER PRIMARY KEY,
    file_path TEXT UNIQUE NOT NULL,
    filename TEXT,

    -- Metadata
    artist TEXT,
    title TEXT,
    album TEXT,
    year INTEGER,
    duration REAL,
    file_format TEXT,  -- mp3/flac/m4a
    file_size INTEGER,

    -- Hashing for duplicate detection
    metadata_hash TEXT,      -- MD5 of normalized artist|title
    file_content_hash TEXT,  -- MD5 of file bytes
    audio_fingerprint TEXT,  -- Optional: acoustic fingerprint

    -- Timestamps
    indexed_at TEXT,
    file_mtime TEXT,
    last_verified TEXT,

    -- Status
    is_active BOOLEAN DEFAULT 1,

    UNIQUE(file_path)
);

CREATE INDEX idx_metadata_hash ON library_index(metadata_hash);
CREATE INDEX idx_content_hash ON library_index(file_content_hash);
CREATE INDEX idx_artist_title ON library_index(artist, title);
CREATE INDEX idx_fingerprint ON library_index(audio_fingerprint);
```

3. **Smart Indexing**:
   - Incremental updates (only scan new/changed files)
   - Progress tracking with Rich library
   - Handles moved/renamed files
   - Periodic re-verification

**Estimated Time**: 6 hours
**Complexity**: Medium
**Dependencies**: mutagen, hashlib (already in use)

---

### **Phase 2: Import Vetting Tool** (6-8 hours)

**Goal**: Check new music against main library before import

#### New Module: `import_vetter.py`

**Features**:

1. **Multi-Level Duplicate Detection**:
   ```python
   class DuplicateChecker:
       def check_duplicates(self, new_file_path) -> DuplicateResult:
           # Level 1: Exact metadata match (fastest)
           if exact_match := self._check_metadata_hash(file):
               return DuplicateResult(is_duplicate=True,
                                    confidence=1.0,
                                    match_type="exact_metadata",
                                    matched_file=exact_match)

           # Level 2: Fuzzy metadata match
           if fuzzy_matches := self._check_fuzzy_metadata(file, threshold=0.8):
               return DuplicateResult(is_duplicate=True,
                                    confidence=fuzzy_matches[0].score,
                                    match_type="fuzzy_metadata",
                                    matched_file=fuzzy_matches[0].file)

           # Level 3: File content hash (exact file duplicate)
           if content_match := self._check_file_hash(file):
               return DuplicateResult(is_duplicate=True,
                                    confidence=1.0,
                                    match_type="exact_file",
                                    matched_file=content_match)

           # Level 4: Audio fingerprint (acoustic match)
           if audio_match := self._check_audio_fingerprint(file):
               return DuplicateResult(is_duplicate=True,
                                    confidence=audio_match.score,
                                    match_type="acoustic",
                                    matched_file=audio_match.file)

           return DuplicateResult(is_duplicate=False)
   ```

2. **Batch Vetting Workflow**:
   ```python
   class ImportVetter:
       def vet_import_folder(self, new_folder_path, main_library_db):
           # Scan new folder
           new_files = self.scanner.scan(new_folder_path)

           # Check each file
           results = {
               'duplicates': [],
               'new_songs': [],
               'uncertain': []  # Fuzzy matches below threshold
           }

           for file in new_files:
               dup_result = self.checker.check_duplicates(file)

               if dup_result.is_duplicate and dup_result.confidence >= 0.8:
                   results['duplicates'].append((file, dup_result))
               elif dup_result.is_duplicate and dup_result.confidence < 0.8:
                   results['uncertain'].append((file, dup_result))
               else:
                   results['new_songs'].append(file)

           return VettingReport(results)
   ```

3. **Interactive Report**:
   - **Duplicates**: List with matched file paths, confidence scores
   - **New Songs**: List for your curation review
   - **Uncertain Matches**: Present for manual decision
   - Options:
     - Auto-skip duplicates
     - Auto-delete duplicates
     - Review uncertain matches
     - Export new songs list

4. **Rich Console UI**:
   ```
   ╔══════════════════════════════════════════════════════════════╗
   ║         Import Vetting Report                                ║
   ╠══════════════════════════════════════════════════════════════╣
   ║                                                              ║
   ║  Scanned: 2,000 files                                        ║
   ║  ✓ Duplicates Found: 487 (24.4%)                            ║
   ║  ⚠ Uncertain Matches: 23 (1.2%)                             ║
   ║  ✨ New Songs: 1,490 (74.5%)                                ║
   ║                                                              ║
   ╠══════════════════════════════════════════════════════════════╣
   ║  Recommendations:                                            ║
   ║  • Skip 487 duplicates (save 2.3 hours of review time)      ║
   ║  • Review 23 uncertain matches (5 minutes)                   ║
   ║  • Focus curation on 1,490 new songs                        ║
   ╚══════════════════════════════════════════════════════════════╝
   ```

**Estimated Time**: 8 hours
**Complexity**: Medium-High
**Dependencies**: Uses library_indexer database

---

### **Phase 3: CLI Integration** (2-3 hours)

#### Add New Commands:

```python
# music_tools_cli/commands/library.py

@app.command("index")
def index_main_library(
    library_path: str = typer.Option(..., "--path", "-p", help="Path to main library"),
    rescan: bool = typer.Option(False, "--rescan", help="Force full rescan"),
    incremental: bool = typer.Option(True, help="Only scan new/changed files")
):
    """Index your main music library for duplicate detection."""
    indexer = LibraryIndexer()
    indexer.index_library(library_path, rescan=rescan, incremental=incremental)


@app.command("vet-import")
def vet_import_folder(
    import_folder: str = typer.Option(..., "--folder", "-f", help="Folder to vet"),
    library_db: str = typer.Option(None, "--library", help="Library database path"),
    auto_skip: bool = typer.Option(False, "--auto-skip", help="Auto-skip duplicates"),
    threshold: float = typer.Option(0.8, "--threshold", help="Fuzzy match threshold")
):
    """Vet a new import folder against your main library."""
    vetter = ImportVetter(library_db)
    report = vetter.vet_import_folder(import_folder, auto_skip=auto_skip, threshold=threshold)
    report.display()

    if typer.confirm("Export new songs list?"):
        report.export_new_songs("new_songs_to_review.txt")


@app.command("verify-library")
def verify_library(
    library_path: str = typer.Option(..., "--path", "-p"),
    check_missing: bool = typer.Option(True, help="Check for deleted files"),
    check_moved: bool = typer.Option(True, help="Detect moved files")
):
    """Verify library index is up-to-date."""
    indexer = LibraryIndexer()
    indexer.verify_library(library_path, check_missing, check_moved)
```

**Estimated Time**: 3 hours
**Complexity**: Low

---

### **Phase 4: Advanced Features (Optional)** (8-12 hours)

#### A. Audio Fingerprinting
**Library**: `chromaprint` (AcoustID) or `librosa`

**Benefits**:
- Catches exact duplicates even with different metadata
- Detects re-encodes (same recording, different file)
- Language/region variations (different artist spellings)

**Implementation**:
```python
import chromaprint

def generate_audio_fingerprint(file_path):
    """Generate acoustic fingerprint using Chromaprint."""
    duration, fingerprint = chromaprint.fingerprint_file(file_path)
    return fingerprint

def compare_fingerprints(fp1, fp2, threshold=0.9):
    """Compare two fingerprints and return similarity score."""
    # Use Hamming distance or other similarity metric
    return similarity_score
```

**Time**: 6 hours
**Complexity**: Medium
**Dependencies**: `pyacoustid`, `chromaprint`

---

#### B. Smart Duplicate Resolution
**Feature**: AI-powered decision on which duplicate to keep

**Criteria**:
- Higher bitrate (better quality)
- FLAC > MP3 > M4A
- Better metadata completeness
- Newer file (if same quality)
- User preferences

**Implementation**:
```python
class DuplicateResolver:
    def choose_best_version(self, duplicates: List[MusicFile]) -> MusicFile:
        scores = []
        for file in duplicates:
            score = 0
            score += self._quality_score(file)      # Bitrate, format
            score += self._metadata_score(file)     # Completeness
            score += self._recency_score(file)      # File age
            scores.append((file, score))

        return max(scores, key=lambda x: x[1])[0]
```

**Time**: 4 hours

---

#### C. Continuous Monitoring
**Feature**: Watch folders for new files, auto-check duplicates

**Implementation**:
```python
from watchdog.observers import Observer

class LibraryWatcher:
    def watch_import_folder(self, folder_path):
        """Monitor folder for new files, auto-check duplicates."""
        observer = Observer()
        observer.schedule(ImportHandler(self.vetter), folder_path, recursive=True)
        observer.start()
```

**Time**: 4 hours

---

## 4. 📊 IMPLEMENTATION PLAN SUMMARY

### Recommended Phased Approach:

| Phase | Feature | Time | Priority | ROI |
|-------|---------|------|----------|-----|
| **1** | Library Indexer | 6h | Critical | High |
| **2** | Import Vetter | 8h | Critical | Very High |
| **3** | CLI Integration | 3h | High | High |
| **4A** | Audio Fingerprinting | 6h | Medium | Medium |
| **4B** | Smart Resolution | 4h | Low | Medium |
| **4C** | Continuous Monitoring | 4h | Low | Low |

**Total Core Features (Phases 1-3)**: 17 hours
**Total with Advanced Features**: 31 hours

---

## 5. 🚀 QUICK WIN: Leverage Existing Tools

### **Immediate Solution (0 hours - Use Now!)**

You can **use the existing Library Comparison tool** for your workflow:

```bash
# Navigate to your Music Tools directory
cd "/home/claude-flow/projects/ActiveProjects/Music Tools/Music Tools Dev"

# Run the library comparison tool
python3 apps/music-tools/music_tools_cli/cli.py library compare

# Or via legacy tool directly
python3 apps/music-tools/legacy/Library\ Comparison/library_comparison.py
```

**Interactive Workflow**:
1. It will prompt for Library A (your main library path)
2. Then prompt for Library B (new import folder)
3. Choose matching mode: Exact or Fuzzy
4. It will show all duplicates found
5. Option to delete duplicates from Library B (new folder)
6. Keeps your main library intact

**Pros**:
- ✅ Works today, no development needed
- ✅ Fuzzy matching (80% threshold)
- ✅ Safe deletion (only from new folder)
- ✅ Interactive confirmation

**Cons**:
- ❌ Slow for large libraries (rescans every time)
- ❌ No database caching
- ❌ Manual process each time

---

## 6. 💡 RECOMMENDED IMMEDIATE ACTION

### Option 1: Use Existing Tool (Today)
Try the existing `library compare` command with your workflow:
- Test with a small import folder first
- Measure performance with your library size
- See if fuzzy matching catches your duplicates

### Option 2: Build Enhanced Solution (Next Week)
Implement Phases 1-3 (17 hours):
- Much faster with database indexing
- Batch processing capability
- Better reporting
- Designed for your exact workflow

---

## 7. ✨ ENHANCEMENT PRIORITIES

### If Existing Tool Works But Needs Improvement:

**Priority 1 - Speed** (Most Important):
- Add SQLite database for main library
- Index on first run, then only check new files
- **Impact**: 100x faster for large libraries

**Priority 2 - Workflow** (High Value):
- Batch import vetting mode
- Auto-skip duplicates option
- Export new songs list
- **Impact**: Saves hours per import session

**Priority 3 - Accuracy** (Medium Value):
- Audio fingerprinting for better matching
- Handles metadata variations better
- **Impact**: Catches more duplicates

**Priority 4 - Automation** (Nice to Have):
- Folder watching
- Auto-import workflow
- **Impact**: Convenience

---

## 8. 📝 NEXT STEPS

1. **Try existing tool** with your workflow
2. **Provide feedback**:
   - Does fuzzy matching work well?
   - Is it too slow?
   - Any false positives/negatives?
3. **Decide on enhancements** based on actual usage
4. **Implement in phases** starting with database indexing

---

**Ready to proceed?** I can:
- A) Help you test the existing tool right now
- B) Build the enhanced solution (Phases 1-3)
- C) Start with just Phase 1 (library indexing)
- D) Something else

What would you like to do?

---

*Analysis completed: 2025-11-19*
*Existing features: Metadata-based duplicate detection ✅*
*Enhancement: Database-backed library indexing needed*
