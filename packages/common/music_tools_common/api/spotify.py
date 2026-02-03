"""
Spotify API client.
"""

from .base import BaseAPIClient


class SpotifyClient(BaseAPIClient):
    """Spotify API client."""

    def __init__(self):
        super().__init__("https://api.spotify.com/v1")
