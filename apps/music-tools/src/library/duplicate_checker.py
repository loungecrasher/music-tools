"""
Duplicate detection for music files.

Provides multi-level duplicate detection using metadata and file content hashing.
"""

import logging
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    from mutagen import File as MutagenFile
except ImportError:
    MutagenFile = None

from .database import LibraryDatabase
from .hash_utils import calculate_file_hash, calculate_metadata_hash
from .models import DuplicateResult, LibraryFile

logger = logging.getLogger(__name__)

# Constants
DEFAULT_FUZZY_THRESHOLD: float = 0.8
MIN_FUZZY_THRESHOLD: float = 0.0
MAX_FUZZY_THRESHOLD: float = 1.0
MAX_DISPLAY_YEAR_LENGTH: int = 4  # Extract first 4 chars for year
MIN_VALID_YEAR: int = 1000  # Minimum reasonable year
MAX_VALID_YEAR: int = 9999  # Maximum reasonable year


class DuplicateChecker:
    """Multi-level duplicate detection for music files."""

    def __init__(self, library_db: LibraryDatabase):
        """Initialize duplicate checker.

        Args:
            library_db: LibraryDatabase instance. Must not be None.

        Raises:
            ValueError: If library_db is None.
        """
        if library_db is None:
            raise ValueError("library_db cannot be None")

        self.db = library_db

    def check_file(
        self,
        file_path: str,
        fuzzy_threshold: float = DEFAULT_FUZZY_THRESHOLD,
        use_fuzzy: bool = True,
        use_content_hash: bool = True
    ) -> DuplicateResult:
        """Check if a file is a duplicate.

        Uses multi-level detection:
        1. Exact metadata hash match (100% confidence)
        2. File content hash match (100% confidence)
        3. Fuzzy metadata match (threshold-based confidence)

        Args:
            file_path: Path to file to check. Must not be None or empty.
            fuzzy_threshold: Similarity threshold for fuzzy matching.
                           Must be between 0.0 and 1.0. Default 0.8.
            use_fuzzy: If True, perform fuzzy metadata matching. Default True.
            use_content_hash: If True, check file content hash. Default True.

        Returns:
            DuplicateResult with match information. Never None.

        Raises:
            ValueError: If file_path is empty or fuzzy_threshold is out of range.
        """
        # Input validation
        if not file_path:
            raise ValueError("file_path cannot be None or empty")

        if not MIN_FUZZY_THRESHOLD <= fuzzy_threshold <= MAX_FUZZY_THRESHOLD:
            raise ValueError(
                f"fuzzy_threshold must be between {MIN_FUZZY_THRESHOLD} and {MAX_FUZZY_THRESHOLD}, "
                f"got {fuzzy_threshold}"
            )
        # Validate file path
        try:
            resolved_path = Path(file_path).resolve()
            if not resolved_path.exists():
                logger.warning(f"File does not exist: {file_path}")
                return DuplicateResult(
                    is_duplicate=False,
                    confidence=0.0,
                    match_type='none',
                    matched_file=None,
                    all_matches=[]
                )
        except (OSError, ValueError) as e:
            logger.error(f"Invalid file path {file_path}: {e}")
            return DuplicateResult(
                is_duplicate=False,
                confidence=0.0,
                match_type='none',
                matched_file=None,
                all_matches=[]
            )

        # Extract metadata from file
        library_file = self._extract_metadata(resolved_path)

        if library_file is None:
            return DuplicateResult(
                is_duplicate=False,
                confidence=0.0,
                match_type='none',
                matched_file=None,
                all_matches=[]
            )

        # Level 1: Check exact metadata hash
        exact_match = self._check_metadata_hash(library_file)
        if exact_match:
            return DuplicateResult(
                is_duplicate=True,
                confidence=1.0,
                match_type='exact_metadata',
                matched_file=exact_match,
                all_matches=[(exact_match, 1.0)]
            )

        # Level 2: Check file content hash
        if use_content_hash:
            content_match = self._check_file_hash(library_file)
            if content_match:
                return DuplicateResult(
                    is_duplicate=True,
                    confidence=1.0,
                    match_type='exact_file',
                    matched_file=content_match,
                    all_matches=[(content_match, 1.0)]
                )

        # Level 3: Fuzzy metadata matching
        if use_fuzzy and library_file.artist and library_file.title:
            fuzzy_matches = self._check_fuzzy_metadata(library_file, fuzzy_threshold)

            if fuzzy_matches:
                # Get best match
                best_match, best_score = fuzzy_matches[0]

                return DuplicateResult(
                    is_duplicate=best_score >= fuzzy_threshold,
                    confidence=best_score,
                    match_type='fuzzy_metadata',
                    matched_file=best_match,
                    all_matches=fuzzy_matches
                )

        # No match found
        return DuplicateResult(
            is_duplicate=False,
            confidence=0.0,
            match_type='none',
            matched_file=None,
            all_matches=[]
        )

    def _extract_metadata(self, file_path: Path) -> Optional[LibraryFile]:
        """Extract metadata from file for comparison.

        Args:
            file_path: Path to music file. Must not be None.

        Returns:
            LibraryFile with extracted metadata, or None on error.

        Note:
            Logs warnings but returns None on any error rather than raising exceptions.
        """
        if file_path is None:
            logger.error("_extract_metadata called with None file_path")
            return None
        if MutagenFile is None:
            raise ImportError("mutagen library is required for metadata extraction")

        try:
            # Get file stats
            stat = file_path.stat()
            file_size = stat.st_size

            # Extract metadata using mutagen
            audio = MutagenFile(str(file_path))

            if audio is None:
                return None

            # Extract common tags (using local helper methods for tag extraction)
            artist = self._extract_tag(audio, 'artist')
            title = self._extract_tag(audio, 'title')
            album = self._extract_tag(audio, 'album')
            year = self._extract_year(audio)
            duration = audio.info.length if hasattr(audio.info, 'length') else None

            # Calculate hashes using shared hash_utils
            # Pass filename to prevent false matches for files without metadata
            metadata_hash = calculate_metadata_hash(artist, title, filename=file_path.name)
            file_content_hash = calculate_file_hash(file_path)

            # If file hash calculation failed, use a fallback
            if file_content_hash is None:
                logger.warning(f"Failed to calculate file hash for {file_path}, using placeholder")
                file_content_hash = "HASH_FAILED"

            return LibraryFile(
                file_path=str(file_path),
                filename=file_path.name,
                artist=artist,
                title=title,
                album=album,
                year=year,
                duration=duration,
                file_format=file_path.suffix.lower().lstrip('.'),
                file_size=file_size,
                metadata_hash=metadata_hash,
                file_content_hash=file_content_hash
            )

        except Exception as e:
            logger.warning(f"Error extracting metadata from {file_path}: {e}")
            return None

    def _extract_tag(self, audio, tag_name: str) -> Optional[str]:
        """Extract tag value from audio file.

        Args:
            audio: Mutagen audio object. Must not be None.
            tag_name: Tag name to extract. Must not be None or empty.

        Returns:
            Tag value as string, or None if not found.

        Note:
            Tries multiple tag name variants for cross-format compatibility.
        """
        if audio is None or not tag_name:
            return None
        # Try common tag names
        tag_variants = {
            'artist': ['artist', 'TPE1', '\xa9ART'],
            'title': ['title', 'TIT2', '\xa9nam'],
            'album': ['album', 'TALB', '\xa9alb'],
        }

        variants = tag_variants.get(tag_name, [tag_name])

        for variant in variants:
            if variant in audio:
                value = audio[variant]
                if isinstance(value, list) and len(value) > 0:
                    return str(value[0])
                elif isinstance(value, str):
                    return value

        return None

    def _extract_year(self, audio) -> Optional[int]:
        """Extract year from audio file.

        Args:
            audio: Mutagen audio object. Must not be None.

        Returns:
            Year as integer (4 digits), or None if not found or invalid.

        Note:
            Extracts first 4 characters from date tags and attempts integer conversion.
            Validates year is between 1000 and 9999.
        """
        if audio is None:
            return None

        year_tags = ['date', 'year', 'TDRC', '\xa9day']

        for tag in year_tags:
            if tag in audio:
                value = audio[tag]
                if isinstance(value, list) and len(value) > 0:
                    value = value[0]

                # Try to extract year (first 4 characters)
                year_str = str(value)[:MAX_DISPLAY_YEAR_LENGTH]
                try:
                    year = int(year_str)
                    # Validate year is reasonable
                    if MIN_VALID_YEAR <= year <= MAX_VALID_YEAR:
                        return year
                except (ValueError, TypeError):
                    continue

        return None

    def _check_metadata_hash(self, file: LibraryFile) -> Optional[LibraryFile]:
        """Check for exact metadata hash match.

        Args:
            file: LibraryFile to check. Must not be None.

        Returns:
            Matching LibraryFile from database, or None if no match.

        Note:
            Returns None if file is None or has no metadata_hash.
        """
        if file is None or not hasattr(file, 'metadata_hash') or file.metadata_hash is None:
            return None

        return self.db.get_file_by_metadata_hash(file.metadata_hash)

    def _check_file_hash(self, file: LibraryFile) -> Optional[LibraryFile]:
        """Check for exact file content hash match.

        Args:
            file: LibraryFile to check. Must not be None.

        Returns:
            Matching LibraryFile from database, or None if no match.

        Note:
            Returns None if file is None or has no file_content_hash.
        """
        if file is None or not hasattr(file, 'file_content_hash') or file.file_content_hash is None:
            return None

        return self.db.get_file_by_content_hash(file.file_content_hash)

    def _check_fuzzy_metadata(
        self,
        file: LibraryFile,
        threshold: float,
        cached_tracks: Optional[List[LibraryFile]] = None
    ) -> List[Tuple[LibraryFile, float]]:
        """Check for fuzzy metadata matches.

        Args:
            file: LibraryFile to check. Must not be None.
            threshold: Similarity threshold (0.0-1.0). Must be in valid range.
            cached_tracks: Optional list of LibraryFile objects to check against (optimization).

        Returns:
            List of (LibraryFile, similarity_score) tuples, sorted by score descending.
            Empty list if file has no artist/title or no matches found.

        Note:
            Validates threshold range. Returns empty list on invalid input.
        """
        if file is None:
            logger.warning("_check_fuzzy_metadata called with None file")
            return []

        if not MIN_FUZZY_THRESHOLD <= threshold <= MAX_FUZZY_THRESHOLD:
            logger.warning(f"Invalid threshold {threshold}, must be between 0.0 and 1.0")
            return []

        if not file.artist or not file.title:
            return []

        # Use cached tracks if provided, otherwise query DB
        if cached_tracks is not None:
            candidates = cached_tracks
        else:
            # Get all files with same artist (case-insensitive)
            candidates = self.db.search_by_artist_title(artist=file.artist)

        matches = []

        for candidate in candidates:
            # Skip self-matches (same file path)
            if candidate.file_path == file.file_path:
                continue

            if not candidate.title:
                continue

            # Calculate similarity between titles
            similarity = self._calculate_similarity(
                self._normalize_string(file.title),
                self._normalize_string(candidate.title)
            )

            if similarity >= threshold:
                matches.append((candidate, similarity))

        # Sort by similarity (descending)
        matches.sort(key=lambda x: x[1], reverse=True)

        return matches

    def _normalize_string(self, text: str) -> str:
        """Normalize string for comparison.

        Args:
            text: String to normalize. Can be None or empty.

        Returns:
            Normalized string (lowercase, stripped, common suffixes removed).
            Empty string if input is None or empty.

        Note:
            Removes common metadata variations like "(original mix)", "[official]", etc.
        """
        if not text:
            return ""
        # Remove common variations
        text = text.lower().strip()

        # Remove common prefixes/suffixes
        replacements = [
            (' (original mix)', ''),
            (' (radio edit)', ''),
            (' (album version)', ''),
            (' (extended)', ''),
            (' [official]', ''),
            (' [hd]', ''),
            (' - remastered', ''),
        ]

        for old, new in replacements:
            text = text.replace(old, new)

        return text

    def _calculate_similarity(self, str1: str, str2: str) -> float:
        """Calculate similarity between two strings.

        Uses SequenceMatcher for fuzzy string matching.

        Args:
            str1: First string. Can be None or empty.
            str2: Second string. Can be None or empty.

        Returns:
            Similarity score between 0.0 (no match) and 1.0 (exact match).
            Returns 0.0 if either string is None or empty.

        Note:
            Uses Python's difflib.SequenceMatcher for ratio calculation.
        """
        if not str1 or not str2:
            return 0.0

        return SequenceMatcher(None, str1, str2).ratio()

    def check_batch(
        self,
        file_paths: List[str],
        fuzzy_threshold: float = DEFAULT_FUZZY_THRESHOLD,
        use_fuzzy: bool = True,
        use_content_hash: bool = True
    ) -> List[Tuple[str, DuplicateResult]]:
        """Check multiple files for duplicates.

        Args:
            file_paths: List of file paths to check. Must not be None.
            fuzzy_threshold: Similarity threshold for fuzzy matching.
                           Must be between 0.0 and 1.0. Default 0.8.
            use_fuzzy: If True, perform fuzzy metadata matching. Default True.
            use_content_hash: If True, check file content hash. Default True.

        Returns:
            List of (file_path, DuplicateResult) tuples.
            Empty list if file_paths is None or empty.

        Raises:
            ValueError: If fuzzy_threshold is out of range.

        Note:
            Processes files sequentially. Errors for individual files are logged
            but don't stop the batch process.
        """
        if file_paths is None:
            logger.warning("check_batch called with None file_paths")
            return []

        if not MIN_FUZZY_THRESHOLD <= fuzzy_threshold <= MAX_FUZZY_THRESHOLD:
            raise ValueError(
                f"fuzzy_threshold must be between {MIN_FUZZY_THRESHOLD} and {MAX_FUZZY_THRESHOLD}, "
                f"got {fuzzy_threshold}"
            )

        results = []

        for file_path in file_paths:
            try:
                result = self.check_file(
                    file_path,
                    fuzzy_threshold=fuzzy_threshold,
                    use_fuzzy=use_fuzzy,
                    use_content_hash=use_content_hash
                )
                results.append((file_path, result))
            except Exception as e:
                logger.error(f"Error checking file {file_path} in batch: {e}")
                # Create a "no duplicate" result for failed files
                results.append((file_path, DuplicateResult(
                    is_duplicate=False,
                    confidence=0.0,
                    match_type='none',
                    matched_file=None,
                    all_matches=[]
                )))

        return results

    def check_files_batch(
        self,
        file_paths: List[str],
        fuzzy_threshold: float = DEFAULT_FUZZY_THRESHOLD,
        use_content_hash: bool = True,
        batch_size: int = 500
    ) -> Dict[str, DuplicateResult]:
        """Check multiple files for duplicates using batch operations for 10-30x performance improvement.

        Uses batch hash lookups instead of checking files one-by-one. This is dramatically
        faster when checking many files against a large library.

        Args:
            file_paths: List of file paths to check.
            fuzzy_threshold: Similarity threshold for fuzzy matching (0.0-1.0).
            use_content_hash: If True, check file content hash.
            batch_size: Number of files to process per batch (default 500).

        Returns:
            Dictionary mapping file_path to DuplicateResult.

        Raises:
            ValueError: If file_paths is empty or fuzzy_threshold out of range.

        Performance:
            - Individual checks: ~5-20 files/sec
            - Batch checks: ~100-500 files/sec
            - 10-30x speedup for large batches

        Example:
            >>> checker = DuplicateChecker(db)
            >>> files = ['file1.mp3', 'file2.mp3', ...]
            >>> results = checker.check_files_batch(files)
            >>> for path, result in results.items():
            ...     if result.is_duplicate:
            ...         print(f"{path} is duplicate of {result.matched_file.file_path}")
        """
        if not file_paths:
            raise ValueError("file_paths cannot be None or empty")
        if not MIN_FUZZY_THRESHOLD <= fuzzy_threshold <= MAX_FUZZY_THRESHOLD:
            raise ValueError(
                f"fuzzy_threshold must be between {MIN_FUZZY_THRESHOLD} and {MAX_FUZZY_THRESHOLD}, "
                f"got {fuzzy_threshold}"
            )

        results = {}

        # Extract metadata from all files
        files_metadata = []
        for file_path in file_paths:
            try:
                resolved_path = Path(file_path).resolve()
                if not resolved_path.exists():
                    results[file_path] = DuplicateResult(
                        is_duplicate=False,
                        confidence=0.0,
                        match_type='none',
                        matched_file=None,
                        all_matches=[]
                    )
                    continue

                library_file = self._extract_metadata(resolved_path)
                if library_file:
                    files_metadata.append((file_path, library_file))
                else:
                    results[file_path] = DuplicateResult(
                        is_duplicate=False,
                        confidence=0.0,
                        match_type='none',
                        matched_file=None,
                        all_matches=[]
                    )
            except Exception as e:
                logger.error(f"Error extracting metadata from {file_path}: {e}")
                results[file_path] = DuplicateResult(
                    is_duplicate=False,
                    confidence=0.0,
                    match_type='none',
                    matched_file=None,
                    all_matches=[]
                )

        if not files_metadata:
            return results

        # Batch lookup metadata hashes (10-30x faster than individual lookups)
        metadata_hashes = [f.metadata_hash for _, f in files_metadata]
        metadata_matches = self.db.batch_get_files_by_hashes(
            metadata_hashes,
            hash_type='metadata',
            batch_size=batch_size
        )

        # Batch lookup content hashes if enabled
        content_matches = {}
        if use_content_hash:
            content_hashes = [f.file_content_hash for _, f in files_metadata if f.file_content_hash]
            content_matches = self.db.batch_get_files_by_hashes(
                content_hashes,
                hash_type='content',
                batch_size=batch_size
            )

        # Optimization: Pre-fetch tracks for all artists in this batch
        # This avoids querying the DB for every single file during fuzzy matching
        artist_tracks_cache = {}
        unique_artists = {f.artist for _, f in files_metadata if f.artist}

        for artist in unique_artists:
            try:
                tracks = self.db.search_by_artist_title(artist=artist)
                artist_tracks_cache[artist] = tracks if tracks else []
            except Exception as e:
                logger.warning(f"Failed to pre-fetch tracks for artist {artist}: {e}")

        # Process results
        for file_path, library_file in files_metadata:
            # Level 1: Check exact metadata hash
            metadata_hash_matches = metadata_matches.get(library_file.metadata_hash, [])
            if metadata_hash_matches:
                # Find first match that isn't the file itself
                match = next((m for m in metadata_hash_matches if m.file_path != file_path), None)
                if match:
                    results[file_path] = DuplicateResult(
                        is_duplicate=True,
                        confidence=1.0,
                        match_type='exact_metadata',
                        matched_file=match,
                        all_matches=[(match, 1.0)]
                    )
                    continue

            # Level 2: Check file content hash
            if use_content_hash and library_file.file_content_hash:
                content_hash_matches = content_matches.get(library_file.file_content_hash, [])
                if content_hash_matches:
                    match = next((m for m in content_hash_matches if m.file_path != file_path), None)
                    if match:
                        results[file_path] = DuplicateResult(
                            is_duplicate=True,
                            confidence=1.0,
                            match_type='exact_file',
                            matched_file=match,
                            all_matches=[(match, 1.0)]
                        )
                        continue

            # Level 3: Fuzzy metadata matching (Optimized with batch artist lookups)
            if library_file.artist and library_file.title:
                # Use pre-fetched tracks if available
                cached_tracks = artist_tracks_cache.get(library_file.artist)

                fuzzy_matches = self._check_fuzzy_metadata(
                    library_file,
                    fuzzy_threshold,
                    cached_tracks=cached_tracks
                )

                if fuzzy_matches:
                    best_match, best_score = fuzzy_matches[0]
                    results[file_path] = DuplicateResult(
                        is_duplicate=best_score >= fuzzy_threshold,
                        confidence=best_score,
                        match_type='fuzzy_metadata',
                        matched_file=best_match,
                        all_matches=fuzzy_matches
                    )
                    continue

            # No match found
            results[file_path] = DuplicateResult(
                is_duplicate=False,
                confidence=0.0,
                match_type='none',
                matched_file=None,
                all_matches=[]
            )

        logger.info(f"Batch duplicate check complete: {len(results)} files processed")
        return results
