"""Build and persist a searchable index of track metadata for Serato matching."""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple, Any

from music_tools_common.metadata.reader import MetadataReader
from music_tools_common.utils.fuzzy import find_best_match

from .models import TrackMetadata

logger = logging.getLogger(__name__)

DEFAULT_INDEX_PATH = Path.home() / ".music-tools" / "serato_track_index.json"

# Common audio extensions used when scanning directories
DEFAULT_AUDIO_EXTENSIONS = ['.mp3', '.m4a', '.flac', '.wav', '.aiff', '.aif']


class SeratoTrackIndex:
    """Searchable index of track metadata.

    The index maps ``search_string`` (lower-cased ``"artist title"``) to
    :class:`TrackMetadata` objects and can be persisted as JSON for fast
    reloading.

    Parameters
    ----------
    index_path : Path, optional
        Where to save/load the JSON file.  Defaults to
        ``~/.music-tools/serato_track_index.json``.
    """

    def __init__(self, index_path: Optional[Path] = None) -> None:
        self.index_path = Path(index_path) if index_path else DEFAULT_INDEX_PATH
        self.tracks: Dict[str, TrackMetadata] = {}
        self.source: Optional[str] = None
        self.built_at: Optional[str] = None

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self) -> None:
        """Write the current index to *index_path* as JSON."""
        self.index_path.parent.mkdir(parents=True, exist_ok=True)

        index_data = {
            'version': 1,
            'built_at': self.built_at or datetime.now().isoformat(),
            'source': self.source or '',
            'track_count': len(self.tracks),
            'tracks': {
                search_string: meta.to_dict()
                for search_string, meta in self.tracks.items()
            },
        }

        with open(self.index_path, 'w', encoding='utf-8') as fh:
            json.dump(index_data, fh, indent=2)

        logger.info("Index saved to %s (%d tracks)", self.index_path, len(self.tracks))

    def load(self) -> int:
        """Load an existing JSON index from *index_path*.

        Returns
        -------
        int
            Number of tracks loaded.

        Raises
        ------
        FileNotFoundError
            If the index file does not exist.
        ValueError
            If the file is corrupt or has an unsupported version.
        """
        if not self.index_path.exists():
            raise FileNotFoundError(f"Index file not found: {self.index_path}")

        try:
            with open(self.index_path, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Index file is corrupted: {exc}") from exc

        version = data.get('version')
        if version != 1:
            raise ValueError(
                f"Unsupported index version: {version}. Please rebuild the index."
            )

        self.source = data.get('source', '')
        self.built_at = data.get('built_at', '')

        self.tracks = {}
        for search_string, track_data in data.get('tracks', {}).items():
            self.tracks[search_string] = TrackMetadata.from_dict(track_data)

        logger.info(
            "Loaded index with %d tracks (built %s)", len(self.tracks), self.built_at
        )
        return len(self.tracks)

    # ------------------------------------------------------------------
    # Building from a directory scan
    # ------------------------------------------------------------------

    def build_from_directory(
        self,
        directory: str,
        extensions: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> int:
        """Recursively scan *directory* for audio files and extract metadata.

        Parameters
        ----------
        directory : str
            Root directory to scan.
        extensions : list of str, optional
            File extensions to include (with leading dot).  Defaults to
            ``DEFAULT_AUDIO_EXTENSIONS``.
        progress_callback : callable, optional
            Called with ``(processed, total)`` after each file.

        Returns
        -------
        int
            Number of tracks successfully indexed.
        """
        if extensions is None:
            extensions = list(DEFAULT_AUDIO_EXTENSIONS)

        dir_path = Path(directory)
        if not dir_path.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        if not dir_path.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {directory}")

        # Normalise extensions
        extensions = [
            ext.lower() if ext.startswith('.') else f'.{ext.lower()}'
            for ext in extensions
        ]

        logger.info("Scanning directory: %s (extensions: %s)", directory, extensions)

        # Collect all matching files, deduplicating via resolved paths
        unique_files: Dict[str, Path] = {}
        for ext in extensions:
            for file_path in dir_path.rglob(f'*{ext}'):
                try:
                    resolved = file_path.resolve()
                    unique_files[str(resolved)] = resolved
                except Exception:
                    continue

        all_files = list(unique_files.values())
        if not all_files:
            logger.warning("No audio files found in %s", directory)
            return 0

        logger.info("Found %d audio files", len(all_files))

        track_count = 0
        skipped_count = 0

        for idx, file_path in enumerate(all_files):
            file_str = str(file_path)

            meta = MetadataReader.read(file_str, fallback_to_filename=True)

            if meta and meta.get('artist') and meta.get('title'):
                parent_folder = file_path.parent.name
                tm = TrackMetadata(
                    path=file_str,
                    artist=meta['artist'],
                    title=meta['title'],
                    crate_name=f"directory:{parent_folder}",
                )
                self.tracks[tm.search_string] = tm
                track_count += 1
            else:
                skipped_count += 1
                logger.debug("Skipped (no metadata): %s", file_path.name)

            if progress_callback is not None:
                progress_callback(idx + 1, len(all_files))

        self.source = f"directory:{directory}"
        self.built_at = datetime.now().isoformat()

        logger.info(
            "Directory scan complete: indexed %d, skipped %d",
            track_count,
            skipped_count,
        )
        return track_count

    # ------------------------------------------------------------------
    # Building from a Serato crate family
    # ------------------------------------------------------------------

    def build_from_crate_family(
        self,
        serato_path: Optional[Path],
        source_crate: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> int:
        """Populate the index from a Serato crate family.

        Uses :class:`CrateManager` internally to read crate files and
        extract metadata via :class:`MetadataReader`.

        Parameters
        ----------
        serato_path : Path or None
            Serato data folder.  ``None`` uses the default.
        source_crate : str
            Name prefix of the crate family.
        progress_callback : callable, optional
            Called with ``(processed, total)`` after each track.

        Returns
        -------
        int
            Number of tracks successfully indexed.
        """
        # Import here to avoid circular dependency at module level
        from .crate_manager import CrateManager

        manager = CrateManager(serato_path)
        loaded = manager.load_tracks_from_crate_family(
            source_crate, progress_callback=progress_callback
        )

        self.tracks.update(loaded)
        self.source = source_crate
        self.built_at = datetime.now().isoformat()

        logger.info(
            "Crate family scan complete: %d tracks from '%s'",
            len(loaded),
            source_crate,
        )
        return len(loaded)

    # ------------------------------------------------------------------
    # Searching
    # ------------------------------------------------------------------

    def find_matches(
        self,
        artist: str,
        title: str,
        threshold: int = 75,
    ) -> Tuple[Optional[TrackMetadata], List[Tuple[TrackMetadata, int]], int]:
        """Find the best matching track in the index.

        Parameters
        ----------
        artist : str
            Artist name to search for.
        title : str
            Track title to search for.
        threshold : int
            Minimum fuzzy-match score (0--100).

        Returns
        -------
        tuple
            ``(best_match, [(track, score), ...], best_score)``
            or ``(None, [], 0)`` when no match exceeds the threshold.
        """
        query = f"{artist} {title}"
        return find_best_match(query, self.tracks, threshold=threshold)
