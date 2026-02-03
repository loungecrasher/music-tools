"""
Deezer authentication.
"""
import requests
from typing import Optional
import logging

from ..config import config_manager

logger = logging.getLogger('music_tools_common.auth.deezer')


class DeezerAuthManager:
    """Deezer authentication manager."""
    
    def __init__(self):
        self.session: Optional[requests.Session] = None
    
    def get_client(self) -> requests.Session:
        """Get authenticated Deezer session."""
        if self.session is not None:
            return self.session
        
        config = config_manager.load_config('deezer')
        email = config.get('email')
        
        if not email:
            raise ValueError("Missing Deezer credentials")
        
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': 'application/json'
        })
        session.email = email
        
        self.session = session
        return session


deezer_auth = DeezerAuthManager()


def get_deezer_client() -> requests.Session:
    """Get Deezer client."""
    return deezer_auth.get_client()
