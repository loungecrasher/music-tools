"""
Deezer API client.
"""
from .base import BaseAPIClient


class DeezerClient(BaseAPIClient):
    """Deezer API client."""

    def __init__(self):
        super().__init__("https://api.deezer.com")
