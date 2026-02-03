"""Menu handler modules for Music Tools.

Re-exports all handler functions for use in menu.py.
"""

from .external_handlers import run_edm_blog_scraper, run_music_country_tagger, run_tool
from .library_handlers import (
    run_candidate_history_add,
    run_candidate_history_check,
    run_library_index,
    run_library_stats,
    run_library_vet,
    run_process_new_music,
    run_smart_cleanup_menu,
)
from .serato_handlers import run_serato_build_index, run_serato_csv_to_crate, run_serato_list_crates
from .spotify_handlers import (
    run_recent_tracks_aggregator,
    run_spotify_collect_from_folder,
    run_spotify_playlist_manager,
    run_spotify_tracks_after_date,
)

__all__ = [
    # Library
    'run_process_new_music',
    'run_library_index',
    'run_library_vet',
    'run_library_stats',
    'run_smart_cleanup_menu',
    'run_candidate_history_add',
    'run_candidate_history_check',
    # Spotify
    'run_spotify_playlist_manager',
    'run_spotify_tracks_after_date',
    'run_spotify_collect_from_folder',
    'run_recent_tracks_aggregator',
    # External
    'run_tool',
    'run_edm_blog_scraper',
    'run_music_country_tagger',
    # Serato
    'run_serato_build_index',
    'run_serato_csv_to_crate',
    'run_serato_list_crates',
]
