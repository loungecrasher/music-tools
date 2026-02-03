#!/usr/bin/env python3
"""
Script to update Spotify configuration.
"""

import json
import os
import sys

# Get the current directory
current_dir = os.path.dirname(os.path.realpath(__file__))

# Path to the config file
config_path = os.path.join(current_dir, "config", "spotify_config.json")

# New configuration
new_config = {
    "client_id": os.environ.get("SPOTIPY_CLIENT_ID", "YOUR_CLIENT_ID_HERE"),
    "client_secret": os.environ.get("SPOTIPY_CLIENT_SECRET", "YOUR_CLIENT_SECRET_HERE"),
    "redirect_uri": "http://localhost:8888/callback",
}

try:
    # Write the new configuration
    with open(config_path, "w") as f:
        json.dump(new_config, f, indent=2)

    # Set secure permissions
    os.chmod(config_path, 0o600)

    print(f"Spotify configuration updated successfully at {config_path}")
except Exception as e:
    print(f"Error updating Spotify configuration: {str(e)}")
    sys.exit(1)
