"""
API clients for music services.
"""

from .base import BaseAPIClient
from .spotify import SpotifyClient
from .deezer import DeezerClient

__all__ = [
    'BaseAPIClient',
    'SpotifyClient',
    'DeezerClient',
]
