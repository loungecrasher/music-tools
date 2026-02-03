"""
Authentication for Music Tools services.
"""

from .base import AuthManager, DeezerAuth, SpotifyAuth
from .deezer import deezer_auth, get_deezer_client
from .spotify import get_spotify_client, spotify_auth

__all__ = [
    'AuthManager',
    'SpotifyAuth',
    'DeezerAuth',
    'get_spotify_client',
    'spotify_auth',
    'get_deezer_client',
    'deezer_auth',
]
