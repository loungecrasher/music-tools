"""
Base API client.
"""

import logging
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger("music_tools_common.api")


class BaseAPIClient:
    """Base class for API clients."""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
        """Make GET request."""
        try:
            response = self.session.get(f"{self.base_url}/{endpoint}", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"API request failed: {e}")
            return None
