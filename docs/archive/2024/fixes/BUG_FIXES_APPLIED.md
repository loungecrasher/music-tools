# Bug Fixes Applied - Duplicate Detection System

**Date:** 2025-11-19
**Status:** IN PROGRESS
**Files Fixed:** 1 of 6 (models.py complete)

---

## ✅ COMPLETED: models.py (All 13 bugs fixed)

### Critical Bugs Fixed

1. **✅ Fixed: Missing Timezone Information** (Lines 6, 63, 237)
   - Added `from datetime import timezone`
   - Changed `datetime.now()` to `datetime.now(timezone.utc)`
   - Affects: LibraryFile.__post_init__, VettingReport.__post_init__

2. **✅ Fixed: No Error Handling in from_dict()** (Lines 119-168)
   - Added comprehensive error handling
   - Validates required fields
   - Safe datetime parsing with try-except
   - Validates and sanitizes file_size
   - Added logging for warnings

3. **✅ Fixed: Empty String Metadata Hash Collisions** (Lines 72-82)
   - Modified metadata_key property
   - Uses `__filename__|{filename}` when both artist and title are empty
   - Prevents all untagged files from having same hash

### High Severity Bugs Fixed

4. **✅ Fixed: __post_init__ Side Effects** (Lines 48-70)
   - Only sets indexed_at for NEW objects (id is None)
   - Added try-except for Path operations
   - Graceful fallback to "unknown" for invalid paths

5. **✅ Fixed: DuplicateResult Validation** (Lines 181-195)
   - Added __post_init__ with validation
   - Validates confidence range (0.0-1.0)
   - Validates match_type against whitelist
   - Logs warning for inconsistent states

6. **✅ Fixed: VettingReport Validation** (Lines 234-247)
   - Added validation in __post_init__
   - Checks total_files >= 0
   - Checks threshold in range [0.0, 1.0]
   - Checks scan_duration >= 0

### Medium Severity Bugs Fixed

7. **✅ Fixed: Percentage Calculation Edge Cases** (Lines 264-278)
   - Added rounding to 2 decimal places
   - Added min(100.0, ...) to cap percentages
   - Consistent with other percentage methods

8. **✅ Fixed: Division Safety in size_mb** (Lines 91-96)
   - Added check for negative file_size
   - Returns 0.0 for invalid sizes

9. **✅ Fixed: get_format_percentages Validation** (Lines 320-332)
   - Skips negative counts
   - Rounds to 2 decimal places
   - Caps at 100.0%

### Low Severity Bugs Fixed

10. **✅ Fixed: Type Hints** (Lines 7, 98, 120, 320)
    - Added `from typing import Dict, Any`
    - Changed `dict` to `Dict[str, Any]` or `Dict[str, float]`
    - More specific type annotations

11. **✅ Fixed: String Handling in to_dict()** (Lines 98-117)
    - Explicit str() conversions
    - max(0, int(file_size)) for safety

12. **✅ Fixed: Logging Setup** (Lines 9-11)
    - Added `import logging`
    - Created module logger
    - Used throughout for warnings

13. **✅ Fixed: Documentation** (Throughout)
    - Updated docstrings to mention validation
    - Added parameter descriptions

---

## 🔄 IN PROGRESS: Remaining Files

### Next: Create hash_utils.py

Need to extract 135 lines of duplicated code from indexer.py and duplicate_checker.py:

```python
# src/library/hash_utils.py
"""
Shared hashing utilities for library indexing and duplicate detection.
"""

import hashlib
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def calculate_metadata_hash(artist: Optional[str], title: Optional[str]) -> str:
    """Calculate MD5 hash of normalized metadata.

    Args:
        artist: Artist name (or None)
        title: Track title (or None)

    Returns:
        MD5 hash as hex string

    Note:
        If both artist and title are empty, returns a special marker to prevent
        false matches between all untagged files.
    """
    artist_norm = (artist or '').strip().lower()
    title_norm = (title or '').strip().lower()

    # If both empty, use special marker
    if not artist_norm and not title_norm:
        return "NO_METADATA"

    metadata_key = f"{artist_norm}|{title_norm}"
    return hashlib.md5(metadata_key.encode('utf-8')).hexdigest()


def calculate_file_hash(file_path: Path, chunk_size: int = 65536) -> Optional[str]:
    """Calculate MD5 hash of file content (first and last 64KB for speed).

    Args:
        file_path: Path to file
        chunk_size: Size of chunks to hash (default 64KB)

    Returns:
        MD5 hash as hex string, or None on error

    Note:
        For performance, only first and last 64KB are hashed for files > 128KB.
        This is sufficient for duplicate detection but may miss differences in
        the middle of files. File size should be used as additional verification.
    """
    try:
        file_size = file_path.stat().st_size
    except (OSError, PermissionError) as e:
        logger.warning(f"Cannot get file size for hashing {file_path}: {e}")
        return None

    hasher = hashlib.md5()

    try:
        with open(file_path, 'rb') as f:
            # Hash first chunk
            first_chunk = f.read(chunk_size)
            hasher.update(first_chunk)

            # Hash last chunk if file is large enough
            if file_size >= chunk_size * 2:
                try:
                    f.seek(-chunk_size, 2)
                    last_chunk = f.read(chunk_size)
                    hasher.update(last_chunk)
                except (OSError, IOError) as e:
                    logger.warning(f"Could not seek in file {file_path}: {e}")

        return hasher.hexdigest()

    except PermissionError:
        logger.warning(f"Permission denied reading file: {file_path}")
        return None
    except FileNotFoundError:
        logger.warning(f"File not found during hashing: {file_path}")
        return None
    except IOError as e:
        logger.warning(f"I/O error reading file {file_path}: {e}")
        return None
```

### Remaining Critical Fixes Needed:

#### database.py (2 critical bugs)
1. **SQL Injection - Dynamic Column Names** (Lines 160-166, 325-330)
2. **Race Condition in verify_file_exists** (Lines 542-557)

#### indexer.py (2 critical bugs)
1. **Symlink Following Vulnerability** (Line 164) - Add `followlinks=False`
2. **Unhandled OSError in Directory Scan** (Lines 164-171)

#### duplicate_checker.py (2 critical bugs)
1. **Self-Match Detection** (Lines 285-323)
2. **Code Duplication** - Replace with hash_utils.py

#### vetter.py (4 critical bugs)
1. **Silent Partial Failures** (Lines 106-133)
2. **Division by Zero** (Line 261)
3. **Missing UTF-8 Encoding** (Lines 353, 370, 391)
4. **Incorrect Categorization Logic** (Lines 205-217)

#### library.py CLI (1 critical bug)
1. **Broken Import Paths** (Lines 65, 145-146, 216, 256, 301-302)

---

## Summary of models.py Fixes

**Total Bugs in models.py:** 13
**Bugs Fixed:** 13 (100%)
**Lines Changed:** ~45 lines
**New Code Added:** ~30 lines
**Code Improved:** Validation, error handling, type safety

**Key Improvements:**
- ✅ Timezone-aware datetimes throughout
- ✅ Comprehensive input validation
- ✅ Error handling with logging
- ✅ Fixed hash collision for untagged files
- ✅ Proper type hints
- ✅ Defensive programming practices

**Testing Needed:**
- Test from_dict() with invalid data
- Test timezone handling across systems
- Test empty metadata handling
- Test percentage calculations at edge cases
- Test validation errors

---

## Next Steps

1. Create `src/library/hash_utils.py`
2. Fix database.py (SQL injection + race condition)
3. Fix indexer.py (symlinks + error handling)
4. Fix duplicate_checker.py (self-match + use hash_utils)
5. Fix vetter.py (categorization + UTF-8 + validation)
6. Fix library.py (import paths)
7. Run comprehensive tests
8. Create final summary

**Estimated Time Remaining:** 3-4 hours for all fixes

