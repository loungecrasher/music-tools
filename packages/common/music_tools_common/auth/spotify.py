"""
Spotify authentication.
"""
import logging
from typing import Optional

import spotipy
from spotipy.oauth2 import SpotifyOAuth

from ..config import config_manager

logger = logging.getLogger('music_tools_common.auth.spotify')


class SpotifyAuthManager:
    """Spotify authentication manager."""

    def __init__(self):
        self.client: Optional[spotipy.Spotify] = None
        # Comprehensive OAuth scopes for full functionality
        self.scope = " ".join([
            # Playlist management
            "playlist-read-private",
            "playlist-modify-private",
            "playlist-modify-public",
            "playlist-read-collaborative",
            # Library management
            "user-library-read",
            "user-library-modify",
            # User profile and preferences
            "user-read-private",
            "user-read-email",
            "user-top-read",
            "user-read-recently-played",
            # Follow management
            "user-follow-read",
            "user-follow-modify",
        ])

    def get_client(self) -> spotipy.Spotify:
        """Get authenticated Spotify client."""
        if self.client is not None:
            return self.client

        config = config_manager.load_config('spotify')

        client_id = config.get('client_id')
        client_secret = config.get('client_secret')
        # CRITICAL: Must use 127.0.0.1 instead of localhost (Spotify requirement as of Nov 27, 2025)
        redirect_uri = config.get('redirect_uri', 'http://127.0.0.1:8888/callback')

        if not all([client_id, client_secret]):
            raise ValueError("Missing Spotify credentials")

        auth_manager = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=self.scope
        )

        self.client = spotipy.Spotify(auth_manager=auth_manager)
        return self.client


spotify_auth = SpotifyAuthManager()


def get_spotify_client() -> spotipy.Spotify:
    """Get Spotify client."""
    return spotify_auth.get_client()
