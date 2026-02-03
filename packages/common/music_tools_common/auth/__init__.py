"""
Authentication for Music Tools services.
"""

from .base import AuthManager, SpotifyAuth, DeezerAuth
from .spotify import get_spotify_client, spotify_auth
from .deezer import get_deezer_client, deezer_auth

__all__ = [
    'AuthManager',
    'SpotifyAuth',
    'DeezerAuth',
    'get_spotify_client',
    'spotify_auth',
    'get_deezer_client',
    'deezer_auth',
]
