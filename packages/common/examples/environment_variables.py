"""
Environment Variables Example for music_tools_common.config

This example demonstrates how environment variables override file-based configuration.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import ConfigManager


def main():
    """Demonstrate environment variable override."""

    print("=" * 60)
    print("Environment Variables Override Example")
    print("=" * 60)

    # Initialize the configuration manager
    manager = ConfigManager(app_name="music_tools_example")

    print("\n1. Loading configuration without environment variables...")
    spotify_config = manager.load_config("spotify", use_cache=False)
    print(f"   Client ID: {spotify_config.get('client_id', 'Not set')}")
    print(f"   Redirect URI: {spotify_config.get('redirect_uri', 'Not set')}")

    # Simulate setting environment variables
    print("\n2. Setting environment variables...")
    os.environ["SPOTIPY_CLIENT_ID"] = "test_client_id_from_env"
    os.environ["SPOTIPY_REDIRECT_URI"] = "http://env-override.com/callback"
    print("   SPOTIPY_CLIENT_ID=test_client_id_from_env")
    print("   SPOTIPY_REDIRECT_URI=http://env-override.com/callback")

    # Load configuration again - environment variables should override
    print("\n3. Reloading configuration...")
    spotify_config = manager.load_config("spotify", use_cache=False)
    print(f"   Client ID: {spotify_config.get('client_id')}")
    print(f"   Redirect URI: {spotify_config.get('redirect_uri')}")

    print("\n✓ Environment variables successfully override file-based config!")

    # Clean up environment variables
    print("\n4. Cleaning up environment variables...")
    del os.environ["SPOTIPY_CLIENT_ID"]
    del os.environ["SPOTIPY_REDIRECT_URI"]

    print("\n" + "=" * 60)
    print("Key Takeaways:")
    print("- Environment variables ALWAYS take priority")
    print("- Store sensitive data (API keys) in .env file or environment")
    print("- Store non-sensitive settings in JSON config files")
    print("=" * 60)


if __name__ == "__main__":
    main()
