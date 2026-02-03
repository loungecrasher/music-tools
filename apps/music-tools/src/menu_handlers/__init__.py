"""Menu handler modules for Music Tools.

Re-exports all handler functions for use in menu.py.
"""

from .library_handlers import (
    run_process_new_music,
    run_library_index,
    run_library_vet,
    run_library_stats,
    run_smart_cleanup_menu,
    run_candidate_history_add,
    run_candidate_history_check,
)
from .spotify_handlers import (
    run_spotify_playlist_manager,
    run_spotify_tracks_after_date,
    run_spotify_collect_from_folder,
    run_recent_tracks_aggregator,
)
from .external_handlers import (
    run_tool,
    run_edm_blog_scraper,
    run_music_country_tagger,
)

__all__ = [
    'run_process_new_music',
    'run_library_index',
    'run_library_vet',
    'run_library_stats',
    'run_smart_cleanup_menu',
    'run_candidate_history_add',
    'run_candidate_history_check',
    'run_spotify_playlist_manager',
    'run_spotify_tracks_after_date',
    'run_spotify_collect_from_folder',
    'run_recent_tracks_aggregator',
    'run_tool',
    'run_edm_blog_scraper',
    'run_music_country_tagger',
]
