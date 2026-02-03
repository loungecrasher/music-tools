# Algorithmic Complexity Analysis

## Executive Summary

Analysis of algorithmic complexity across the Music Tools codebase reveals several performance bottlenecks and optimization opportunities. The overall system demonstrates O(n²) patterns in duplicate detection and linear scans in multiple areas.

**Severity**: MEDIUM-HIGH
**Impact**: User-facing performance degradation with large music libraries
**Priority**: HIGH

---

## Critical Issues

### 1. O(n²) Fuzzy Matching in Duplicate Detection

**Location**: `/apps/music-tools/src/library/duplicate_checker.py:335-389`

**Problem**:
```python
def _check_fuzzy_metadata(self, file: LibraryFile, threshold: float) -> List[Tuple[LibraryFile, float]]:
    # Get all files with same artist (case-insensitive)
    candidates = self.db.search_by_artist_title(artist=file.artist)  # O(n)

    matches = []
    for candidate in candidates:  # O(n)
        # Skip self-matches
        if candidate.file_path == file.file_path:
            continue

        if not candidate.title:
            continue

        # Calculate similarity between titles - O(m) where m is string length
        similarity = self._calculate_similarity(
            self._normalize_string(file.title),
            self._normalize_string(candidate.title)
        )  # SequenceMatcher is O(m²) in worst case
```

**Complexity**: O(n²) with nested loops and string comparison
**Impact**: Performance degrades quadratically with library size

**Recommendation**:
- Implement fuzzy matching indices using n-gram tokenization
- Use Levenshtein distance with early termination
- Consider locality-sensitive hashing (LSH) for approximate matching
- Cache normalized strings to avoid repeated processing

---

### 2. Sequential File Processing in Indexer

**Location**: `/apps/music-tools/src/library/indexer.py:121-159`

**Problem**:
```python
for file_path in music_files:
    try:
        result = self._process_file(
            file_path,
            rescan=rescan,
            incremental=incremental
        )
        # Metadata extraction, hash calculation - all sequential
```

**Complexity**: O(n) but blocking and single-threaded
**Impact**: Wastes CPU resources, slow for large libraries

**Recommendation**:
- Implement parallel file processing using multiprocessing
- Process files in batches with ThreadPoolExecutor
- Use async/await for I/O-bound operations
- Target: 4-8 parallel workers for optimal throughput

---

### 3. Full File Content Hashing

**Location**: `/apps/music-tools/src/library/hash_utils.py:57-145`

**Problem**:
```python
def calculate_file_hash(file_path: Path, chunk_size: int = DEFAULT_CHUNK_SIZE):
    # Only hashes first and last chunks - GOOD
    hasher = hashlib.md5()

    with open(file_path, 'rb') as f:
        # Hash first chunk
        first_chunk = f.read(chunk_size)  # 64KB read
        hasher.update(first_chunk)

        # Hash last chunk if file is large enough
        if file_size >= MINIMUM_FILE_SIZE_FOR_TWO_CHUNKS:
            f.seek(-chunk_size, 2)
            last_chunk = f.read(chunk_size)
            hasher.update(last_chunk)
```

**Complexity**: O(1) per file - OPTIMIZED WELL
**Impact**: Minimal - already uses chunk-based hashing

**Status**: ✅ GOOD - No changes needed

---

### 4. Linear Search in Duplicate Batch Checking

**Location**: `/apps/music-tools/src/library/duplicate_checker.py:446-505`

**Problem**:
```python
def check_batch(self, file_paths: List[str], ...):
    results = []

    for file_path in file_paths:  # O(n)
        try:
            result = self.check_file(  # Each calls _check_fuzzy_metadata: O(n)
                file_path,
                fuzzy_threshold=fuzzy_threshold,
                use_fuzzy=use_fuzzy,
                use_content_hash=use_content_hash
            )
            results.append((file_path, result))
```

**Complexity**: O(n²) - batch processing doesn't optimize individual lookups
**Impact**: HIGH for large batches

**Recommendation**:
- Pre-load all candidates into memory once
- Build in-memory index for artist/title lookups
- Use bulk database operations
- Implement result caching within batch

---

### 5. Web Scraper - Nested Loop with Network I/O

**Location**: `/apps/music-tools/src/scraping/music_scraper.py:614-689`

**Problem**:
```python
with tqdm(total=len(post_urls), desc="Filtering posts by genre", unit="post") as pbar:
    for i, post_url in enumerate(post_urls, 1):  # O(n)
        soup = self.get_page_content(post_url)  # Network I/O - BLOCKING

        if not soup:
            continue

        # Extract genres
        post_genres = self.extract_genre_keywords(soup)  # O(m) - text processing

        # Check if any target genres match
        matching_genres = [genre for genre in target_genres if genre.lower() in [g.lower() for g in post_genres]]  # O(k*m)
```

**Complexity**: O(n * m) with blocking network I/O
**Impact**: CRITICAL - slow user experience, wasted time

**Recommendation**:
- Implement async HTTP requests with aiohttp
- Use connection pooling
- Process responses concurrently as they arrive
- Implement request batching (10-20 concurrent requests)
- Add timeout and retry logic

---

### 6. Tagging Processor - Sequential File Operations

**Location**: `/apps/music-tools/src/tagging/processor.py:528-576`

**Problem**:
```python
def _process_batch(self, files: List[Path], ...):
    # Has concurrent processing BUT limited implementation
    max_workers = min(4, len(files))  # Good

    if max_workers > 1 and len(files) > 2:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Uses threading for I/O-bound work - GOOD
            # BUT: Artist lookup is synchronous and may block
            future_to_file = {
                executor.submit(self._process_file_safe, file_path, dry_run, progress_tracker): file_path
                for file_path in files
            }
```

**Complexity**: O(n/workers) but with thread contention
**Impact**: MEDIUM - better than sequential but not optimal

**Recommendation**:
- Use ProcessPoolExecutor for CPU-bound metadata extraction
- Implement async artist country lookups
- Separate I/O workers from CPU workers
- Increase max_workers to cpu_count()

---

## Performance Metrics by Component

### Library Indexer
| Operation | Current Complexity | Optimized Complexity | Impact |
|-----------|-------------------|----------------------|--------|
| File discovery | O(n) | O(n) - optimal | ✅ Good |
| Metadata extraction | O(n) sequential | O(n/p) parallel | 🟡 Medium |
| Hash calculation | O(1) per file | O(1) - optimal | ✅ Good |
| Database insert | O(n) | O(n) with batching | 🟡 Medium |

### Duplicate Checker
| Operation | Current Complexity | Optimized Complexity | Impact |
|-----------|-------------------|----------------------|--------|
| Exact hash match | O(1) indexed | O(1) - optimal | ✅ Good |
| Fuzzy matching | O(n²) | O(n log n) with LSH | 🔴 Critical |
| String normalization | O(m) | O(m) cached | 🟡 Medium |
| Batch processing | O(n²) | O(n log n) | 🔴 Critical |

### Web Scraper
| Operation | Current Complexity | Optimized Complexity | Impact |
|-----------|-------------------|----------------------|--------|
| Page fetching | O(n) sequential | O(n/c) async | 🔴 Critical |
| Link extraction | O(m) | O(m) - optimal | ✅ Good |
| Genre filtering | O(n*m) | O(n*m) cached | 🟡 Medium |
| Download link extraction | O(k) | O(k) - optimal | ✅ Good |

---

## Recommended Optimizations

### Priority 1: Critical Path Optimizations

1. **Implement Async Web Scraping**
   - Expected improvement: 10-20x faster
   - Effort: Medium
   - Files: `music_scraper.py`

2. **Add Fuzzy Matching Index**
   - Expected improvement: 100-1000x for large libraries
   - Effort: High
   - Files: `duplicate_checker.py`, `database.py`

3. **Parallelize File Processing**
   - Expected improvement: 4-8x faster
   - Effort: Low-Medium
   - Files: `indexer.py`, `processor.py`

### Priority 2: Memory Optimizations

1. **Stream Processing for Large Files**
   - Reduce memory footprint
   - Process files incrementally

2. **Implement Result Caching**
   - Cache normalized strings
   - Cache similarity calculations

### Priority 3: Database Optimizations

1. **Batch Insert Operations**
   - Group database writes
   - Use transactions properly

2. **Query Result Caching**
   - Cache frequent artist lookups
   - Implement query result pooling

---

## Performance Testing Recommendations

### Benchmarks to Implement

1. **Library Indexing Benchmark**
   - Test with 1K, 10K, 100K files
   - Measure time and memory usage
   - Profile hotspots

2. **Duplicate Detection Benchmark**
   - Test fuzzy matching at scale
   - Compare before/after optimization
   - Measure accuracy vs speed tradeoff

3. **Web Scraper Benchmark**
   - Test concurrent vs sequential
   - Measure requests per second
   - Monitor error rates

### Monitoring Metrics

- Files processed per second
- Average processing time per file
- Cache hit rates
- Database query performance
- Memory usage over time
- Thread/process utilization

---

## Conclusion

The codebase has several well-optimized areas (file hashing, database indexing) but suffers from sequential processing and O(n²) algorithms in critical paths. The most impactful optimizations are:

1. Async web scraping (20x improvement)
2. Fuzzy matching optimization (100x+ improvement)
3. Parallel file processing (4-8x improvement)

These optimizations will dramatically improve user experience, especially for large music libraries (10K+ files) and extensive web scraping operations.
