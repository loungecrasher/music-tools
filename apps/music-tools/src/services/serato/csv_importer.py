"""Import a CSV playlist into a Serato crate via fuzzy matching."""
import csv
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from music_tools_common.utils.fuzzy import find_best_match

from .crate_manager import CrateManager
from .models import TrackMetadata
from .track_index import SeratoTrackIndex

logger = logging.getLogger(__name__)


@dataclass
class ImportResult:
    """Outcome of a CSV-to-crate import operation."""

    matched: List[Tuple[str, str, TrackMetadata, int]] = field(default_factory=list)
    """List of (csv_artist, csv_title, matched_track, score)."""

    not_found: List[Tuple[str, str]] = field(default_factory=list)
    """List of (csv_artist, csv_title) that had no match above threshold."""

    multiple_matches: List[Tuple[str, str, List[Tuple[TrackMetadata, int]]]] = field(
        default_factory=list
    )
    """List of (csv_artist, csv_title, [(track, score), ...]) with >1 candidate."""

    crate_path: Optional[str] = None
    """Filesystem path to the created crate, or None if nothing was created."""


class CSVImporter:
    """Read a CSV playlist and create a Serato crate by fuzzy-matching tracks.

    Parameters
    ----------
    track_index : SeratoTrackIndex
        A pre-built index of available tracks for matching.
    crate_manager : CrateManager, optional
        Used to write the resulting crate.  A default instance is created
        if not provided.
    """

    def __init__(
        self,
        track_index: SeratoTrackIndex,
        crate_manager: Optional[CrateManager] = None,
    ) -> None:
        self.track_index = track_index
        self.crate_manager = crate_manager or CrateManager()

    # ------------------------------------------------------------------
    # CSV reading
    # ------------------------------------------------------------------

    @staticmethod
    def read_csv(csv_path: str) -> List[Tuple[str, str]]:
        """Read a CSV file and return ``(artist, title)`` pairs.

        The file must contain ``Artist`` and ``Title`` columns.  Encoding
        is ``utf-8-sig`` to handle an optional BOM.

        Raises
        ------
        FileNotFoundError
            If *csv_path* does not exist.
        ValueError
            If required columns are missing.
        """
        path = Path(csv_path)
        if not path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")

        tracks: List[Tuple[str, str]] = []

        with open(csv_path, 'r', encoding='utf-8-sig') as fh:
            reader = csv.DictReader(fh)

            if reader.fieldnames is None:
                raise ValueError("CSV file is empty or has no header row")

            if 'Artist' not in reader.fieldnames or 'Title' not in reader.fieldnames:
                raise ValueError(
                    f"CSV must have 'Artist' and 'Title' columns. "
                    f"Found columns: {reader.fieldnames}"
                )

            for row in reader:
                artist = row['Artist'].strip()
                title = row['Title'].strip()
                if artist and title:
                    tracks.append((artist, title))

        logger.info("Read %d entries from %s", len(tracks), csv_path)
        return tracks

    # ------------------------------------------------------------------
    # Import workflow
    # ------------------------------------------------------------------

    def import_csv_to_crate(
        self,
        csv_path: str,
        crate_name: str,
        threshold: int = 75,
    ) -> ImportResult:
        """Match a CSV playlist against the track index and build a crate.

        Parameters
        ----------
        csv_path : str
            Path to the CSV file with ``Artist`` and ``Title`` columns.
        crate_name : str
            Name of the Serato subcrate to create.
        threshold : int
            Minimum fuzzy-match score (0--100).

        Returns
        -------
        ImportResult
            Detailed breakdown of matched, unmatched, and ambiguous tracks.
        """
        csv_tracks = self.read_csv(csv_path)
        index_data = self.track_index.tracks

        result = ImportResult()

        for artist, title in csv_tracks:
            query = f"{artist} {title}"
            best_match, all_matches, score = find_best_match(
                query, index_data, threshold=threshold
            )

            if best_match is not None:
                result.matched.append((artist, title, best_match, score))

                if len(all_matches) > 1:
                    result.multiple_matches.append((artist, title, all_matches))
            else:
                result.not_found.append((artist, title))

        # Create the crate if we have matches
        if result.matched:
            track_paths = [match.path for _, _, match, _ in result.matched]
            crate_path = self.crate_manager.create_crate(crate_name, track_paths)
            result.crate_path = str(crate_path)

            logger.info(
                "Imported %d/%d tracks into crate '%s' (%d not found, %d ambiguous)",
                len(result.matched),
                len(csv_tracks),
                crate_name,
                len(result.not_found),
                len(result.multiple_matches),
            )
        else:
            logger.warning(
                "No tracks matched from %s -- crate not created", csv_path
            )

        return result
