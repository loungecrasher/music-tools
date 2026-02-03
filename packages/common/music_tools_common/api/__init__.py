"""
API clients for music services.
"""

from .base import BaseAPIClient
from .deezer import DeezerClient
from .spotify import SpotifyClient

__all__ = [
    "BaseAPIClient",
    "SpotifyClient",
    "DeezerClient",
]
