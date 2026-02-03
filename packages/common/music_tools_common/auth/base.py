"""
Unified authentication module for Music Tools.
Supports authentication for multiple music services.
"""
import json
import os
from typing import Any, Dict, Optional

import requests
import spotipy
from spotipy.oauth2 import SpotifyOAuth


class AuthManager:
    """Base authentication manager class for music services."""

    def __init__(self, config_dir: str = None):
        """Initialize the authentication manager.

        Args:
            config_dir: Directory containing configuration files. If None, uses default.
        """
        if config_dir is None:
            # Default to config directory in the project root
            self.config_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config')
        else:
            self.config_dir = config_dir

        # Ensure config directory exists
        os.makedirs(self.config_dir, exist_ok=True)

        # Initialize clients
        self.spotify_client = None
        self.deezer_client = None

    def load_config(self, service: str) -> Dict[str, Any]:
        """Load configuration for a specific service.

        Args:
            service: Service name (e.g., 'spotify', 'deezer')

        Returns:
            Dict containing configuration values
        """
        config_path = os.path.join(self.config_dir, f'{service}_config.json')

        if not os.path.exists(config_path):
            print(f"Warning: Configuration file for {service} not found at {config_path}")
            return {}

        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Error: Invalid JSON in {service} configuration file")
            return {}
        except Exception as e:
            print(f"Error loading {service} configuration: {str(e)}")
            return {}

    def save_config(self, service: str, config: Dict[str, Any]) -> bool:
        """Save configuration for a specific service.

        Args:
            service: Service name (e.g., 'spotify', 'deezer')
            config: Configuration dictionary to save

        Returns:
            True if successful, False otherwise
        """
        config_path = os.path.join(self.config_dir, f'{service}_config.json')

        try:
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)

            # Set secure permissions
            os.chmod(config_path, 0o600)
            return True
        except Exception as e:
            print(f"Error saving {service} configuration: {str(e)}")
            return False


class SpotifyAuth(AuthManager):
    """Authentication manager for Spotify."""

    def __init__(self, config_dir: str = None):
        """Initialize the Spotify authentication manager."""
        super().__init__(config_dir)
        self.client = None
        self.scope = "playlist-read-private playlist-modify-private playlist-modify-public user-library-read"

    def get_client(self) -> Optional[spotipy.Spotify]:
        """Get an authenticated Spotify client.

        Returns:
            Authenticated Spotify client or None if authentication fails
        """
        if self.client is not None:
            return self.client

        return self.initialize_client()

    def initialize_client(self) -> Optional[spotipy.Spotify]:
        """Initialize or reinitialize the Spotify client.

        Returns:
            Authenticated Spotify client or None if authentication fails
        """
        config = self.load_config('spotify')

        if not config:
            print("Error: Spotify configuration not found")
            return None

        client_id = config.get('client_id')
        client_secret = config.get('client_secret')
        redirect_uri = config.get('redirect_uri', 'http://localhost:8888/callback')

        if not all([client_id, client_secret]):
            print("Error: Missing required Spotify credentials")
            return None

        try:
            print("\nInitializing Spotify client...")
            # Only show part of the client ID for security
            if client_id:
                print(f"Client ID: {client_id[:5]}...{client_id[-5:]}")
            print(f"Redirect URI: {redirect_uri}")

            # Initialize with configured scopes
            auth_manager = SpotifyOAuth(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                scope=self.scope,
                open_browser=True,
                show_dialog=True
            )

            # Initialize client
            sp = spotipy.Spotify(auth_manager=auth_manager)

            # Test the connection and get user info
            user = sp.me()
            print(f"\nSuccessfully connected to Spotify as user: {user['id']}")

            # Test playlist access
            sp.current_user_playlists(limit=1)
            print("✓ Successfully accessed playlists")

            self.client = sp
            return sp

        except Exception as e:
            print(f"\nError initializing Spotify client: {str(e)}")
            print("\nPlease verify in the Spotify Developer Dashboard:")
            print("1. The app settings show these credentials:")
            print(f"   Client ID: {client_id[:5]}...{client_id[-5:] if client_id else ''}")
            print(f"   Redirect URI: {redirect_uri}")
            print("2. Your Spotify account has been authorized for this application")
            print("3. The required scopes are enabled:")
            print(f"   {self.scope}")
            return None

    def ensure_client(self) -> spotipy.Spotify:
        """Ensure we have a working Spotify client.

        Returns:
            Authenticated Spotify client

        Raises:
            Exception: If client initialization fails
        """
        if self.client is None:
            self.client = self.initialize_client()
        if self.client is None:
            raise Exception("Failed to initialize Spotify client")
        return self.client


class DeezerAuth(AuthManager):
    """Authentication manager for Deezer."""

    def __init__(self, config_dir: str = None):
        """Initialize the Deezer authentication manager."""
        super().__init__(config_dir)
        self.client = None
        self.session = requests.Session()

    def get_client(self) -> Optional[requests.Session]:
        """Get an authenticated Deezer client (requests.Session).

        Returns:
            Authenticated requests.Session or None if authentication fails
        """
        if self.client is not None:
            return self.client

        return self.initialize_client()

    def initialize_client(self) -> Optional[requests.Session]:
        """Initialize or reinitialize the Deezer client.

        Returns:
            Authenticated requests.Session or None if authentication fails
        """
        config = self.load_config('deezer')

        if not config:
            print("Error: Deezer configuration not found")
            return None

        email = config.get('email')

        if not email:
            print("Error: Missing required Deezer credentials")
            return None

        try:
            print("\nInitializing Deezer client...")
            print(f"Email: {email}")

            # Set up session with headers
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Accept': 'application/json'
            })

            # Store email in session for later use
            session.email = email

            # Test the connection with a simple API call
            response = session.get('https://api.deezer.com/infos')
            if response.status_code == 200:
                print("✓ Successfully connected to Deezer API")
                self.client = session
                return session
            else:
                print(f"✗ Failed to connect to Deezer API: {response.status_code}")
                return None

        except Exception as e:
            print(f"\nError initializing Deezer client: {str(e)}")
            return None

    def ensure_client(self) -> requests.Session:
        """Ensure we have a working Deezer client.

        Returns:
            Authenticated requests.Session

        Raises:
            Exception: If client initialization fails
        """
        if self.client is None:
            self.client = self.initialize_client()
        if self.client is None:
            raise Exception("Failed to initialize Deezer client")
        return self.client


# Global instances
spotify_auth = SpotifyAuth()
deezer_auth = DeezerAuth()


def get_spotify_client() -> spotipy.Spotify:
    """Get an authenticated Spotify client.

    Returns:
        Authenticated Spotify client

    Raises:
        Exception: If client initialization fails
    """
    return spotify_auth.ensure_client()


def get_deezer_client() -> requests.Session:
    """Get an authenticated Deezer client.

    Returns:
        Authenticated requests.Session

    Raises:
        Exception: If client initialization fails
    """
    return deezer_auth.ensure_client()
