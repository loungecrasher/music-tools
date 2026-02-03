"""Manage Serato crate files -- read, create, and list crate families."""
import logging
from pathlib import Path
from typing import Callable, Dict, List, Optional

from music_tools_common.metadata.reader import MetadataReader
from serato_tools.crate import Crate

from .models import CrateInfo, TrackMetadata

logger = logging.getLogger(__name__)

DEFAULT_SERATO_PATH = Path.home() / "Music" / "_Serato_"


class CrateManager:
    """High-level interface for Serato crate operations.

    Parameters
    ----------
    serato_path : Path, optional
        Root of the Serato data folder.  Defaults to ``~/Music/_Serato_``.
    """

    def __init__(self, serato_path: Optional[Path] = None) -> None:
        self.serato_path = Path(serato_path) if serato_path else DEFAULT_SERATO_PATH
        self.subcrates_dir = self.serato_path / "Subcrates"

    # ------------------------------------------------------------------
    # List helpers
    # ------------------------------------------------------------------

    def list_crate_families(self) -> List[CrateInfo]:
        """Return ``CrateInfo`` for every ``.crate`` file under Subcrates."""
        if not self.subcrates_dir.exists():
            logger.warning("Subcrates directory not found: %s", self.subcrates_dir)
            return []

        results: List[CrateInfo] = []
        for crate_file in sorted(self.subcrates_dir.glob("*.crate")):
            try:
                crate = Crate(str(crate_file))
                track_count = len(crate.get_track_paths())
            except Exception as exc:
                logger.warning("Failed to read crate %s: %s", crate_file.stem, exc)
                track_count = 0

            # A subcrate name contains a separator (e.g. "%%")
            is_subcrate = "%%" in crate_file.stem

            results.append(
                CrateInfo(
                    name=crate_file.stem,
                    path=str(crate_file),
                    track_count=track_count,
                    is_subcrate=is_subcrate,
                )
            )
        return results

    # ------------------------------------------------------------------
    # Read tracks from a crate *family* (parent + subcrates)
    # ------------------------------------------------------------------

    def get_crate_family_files(self, source_crate: str) -> List[Path]:
        """Return all ``.crate`` files whose name starts with *source_crate*."""
        if not self.subcrates_dir.exists():
            logger.error("Subcrates directory not found: %s", self.subcrates_dir)
            return []

        return sorted(self.subcrates_dir.glob(f"{source_crate}*.crate"))

    def get_crate_tracks(self, crate_path: Path) -> List[str]:
        """Load a single crate and return track paths with leading ``/``."""
        try:
            crate = Crate(str(crate_path))
            paths: List[str] = []
            for rel in crate.get_track_paths():
                absolute = rel if rel.startswith('/') else f'/{rel}'
                paths.append(absolute)
            return paths
        except Exception as exc:
            logger.error("Failed to read crate %s: %s", crate_path.stem, exc)
            return []

    def load_tracks_from_crate_family(
        self,
        source_crate: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Dict[str, TrackMetadata]:
        """Load all tracks from a crate family (parent + subcrates).

        Parameters
        ----------
        source_crate : str
            Name prefix of the crate family.
        progress_callback : callable, optional
            Called with ``(processed, total)`` after every track.

        Returns
        -------
        dict
            Mapping ``{search_string: TrackMetadata}``.
        """
        crate_files = self.get_crate_family_files(source_crate)
        if not crate_files:
            logger.error(
                "No crate files found matching '%s' in %s",
                source_crate,
                self.subcrates_dir,
            )
            return {}

        logger.info(
            "Found %d crate(s) in family '%s'", len(crate_files), source_crate
        )

        all_tracks: Dict[str, TrackMetadata] = {}
        track_count = 0
        skipped_count = 0
        total_paths = 0

        # Pre-count for progress reporting
        crate_track_lists: List[tuple] = []
        for crate_file in crate_files:
            paths = self.get_crate_tracks(crate_file)
            crate_track_lists.append((crate_file, paths))
            total_paths += len(paths)

        processed = 0
        for crate_file, track_paths in crate_track_lists:
            crate_name = crate_file.stem
            logger.info("Processing crate: %s (%d tracks)", crate_name, len(track_paths))

            for track_path in track_paths:
                processed += 1
                meta = MetadataReader.read(track_path, fallback_to_filename=True)

                if meta and meta.get('artist') and meta.get('title'):
                    tm = TrackMetadata(
                        path=track_path,
                        artist=meta['artist'],
                        title=meta['title'],
                        crate_name=crate_name,
                    )
                    all_tracks[tm.search_string] = tm
                    track_count += 1
                else:
                    skipped_count += 1
                    logger.debug("Skipped (no metadata): %s", Path(track_path).name)

                if progress_callback is not None:
                    progress_callback(processed, total_paths)

        logger.info(
            "Loaded %d tracks with metadata (skipped %d)", track_count, skipped_count
        )
        return all_tracks

    # ------------------------------------------------------------------
    # Create a crate
    # ------------------------------------------------------------------

    def create_crate(self, name: str, track_paths: List[str]) -> Path:
        """Create (or overwrite) a Serato subcrate with the given tracks.

        Parameters
        ----------
        name : str
            Crate name (without ``.crate`` extension).
        track_paths : list of str
            Absolute file paths to include.  Leading ``/`` is stripped
            before writing because Serato stores relative paths.

        Returns
        -------
        Path
            The path to the created ``.crate`` file.
        """
        crate_path = self.subcrates_dir / f"{name}.crate"
        self.subcrates_dir.mkdir(parents=True, exist_ok=True)

        try:
            crate = Crate(str(crate_path))

            for track_path in track_paths:
                relative = track_path.lstrip('/')
                crate.add_track(relative)

            crate.save(str(crate_path))
            logger.info(
                "Created crate '%s' with %d tracks at %s",
                name,
                len(track_paths),
                crate_path,
            )
            return crate_path
        except Exception as exc:
            logger.error("Failed to create crate '%s': %s", name, exc)
            raise
