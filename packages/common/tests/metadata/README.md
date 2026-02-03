# Metadata Module Tests

This directory contains comprehensive tests for the metadata module, achieving **100% code coverage**.

## Quick Start

### Run All Tests
```bash
# From project root
pytest packages/common/tests/test_metadata.py -v

# Or with coverage
pytest packages/common/tests/test_metadata.py --cov=music_tools_common.metadata --cov-report=term-missing
```

### Run Specific Test Class
```bash
pytest packages/common/tests/test_metadata.py::TestMetadataReader -v
pytest packages/common/tests/test_metadata.py::TestMetadataWriter -v
pytest packages/common/tests/test_metadata.py::TestMetadataIntegration -v
```

### Run Specific Test
```bash
pytest packages/common/tests/test_metadata.py::TestMetadataReader::test_read_mp3_metadata -v
```

## Test Coverage

- **`metadata/__init__.py`**: 100% (10/10 statements)
- **`metadata/reader.py`**: 100% (15/15 statements)
- **`metadata/writer.py`**: 100% (19/19 statements)

**Total**: 49 tests, all passing

## Test Organization

### 1. TestMetadataReader (11 tests)
Tests for reading metadata from audio files.

### 2. TestMetadataWriter (13 tests)
Tests for writing metadata to audio files.

### 3. TestReadMetadataFunction (3 tests)
Tests for convenience function `read_metadata()`.

### 4. TestWriteMetadataFunction (3 tests)
Tests for convenience function `write_metadata()`.

### 5. TestMetadataIntegration (4 tests)
Integration tests for complete workflows.

### 6. TestMetadataEdgeCases (8 tests)
Edge cases and error conditions.

### 7. TestMetadataPerformance (2 tests)
Performance benchmarks.

### 8. TestMetadataDataIntegrity (3 tests)
Data integrity and corruption prevention.

### 9. TestMetadataModuleExports (2 tests)
Module exports verification.

## What's Tested

### File Formats
- MP3, FLAC, M4A, OGG, WMA
- Unsupported formats

### Metadata Fields
- title, artist, album, date, genre

### Error Scenarios
- File not found
- Permission errors
- Corrupted files
- Disk full
- File locking

### Special Cases
- Unicode characters (multilingual)
- Special characters (/, \, :)
- Very long strings
- Empty values
- Null bytes
- Newlines

### Data Integrity
- No file corruption on errors
- No data loss during updates
- Atomic write operations

## Coverage Report

View detailed coverage:
```bash
# Generate HTML report
pytest packages/common/tests/test_metadata.py --cov=music_tools_common.metadata --cov-report=html

# Open in browser
open htmlcov/index.html
```

## Files

- `test_metadata.py` - All metadata tests (795 lines)
- `METADATA_TEST_COVERAGE_REPORT.md` - Detailed coverage report

## Status

✅ **PRODUCTION READY** - 100% coverage, all tests passing, data integrity verified.
