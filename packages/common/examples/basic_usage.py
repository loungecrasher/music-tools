#!/usr/bin/env python3
"""
Basic usage examples for music_tools_common.
"""


def example_config():
    """Configuration management example."""
    from music_tools_common.config import config_manager

    print("=== Configuration Example ===")

    # Load configuration
    spotify_config = config_manager.load_config('spotify')
    print(f"Spotify config loaded: {list(spotify_config.keys())}")

    # Save configuration (non-sensitive data only)
    config_manager.save_config('myapp', {
        'theme': 'dark',
        'language': 'en'
    })

    # Validate configuration
    errors = config_manager.validate_config('spotify')
    if errors:
        print(f"Configuration errors: {errors}")
    else:
        print("✓ Configuration is valid")


def example_database():
    """Database management example."""
    from music_tools_common.database import get_database
    from music_tools_common.database.models import Playlist

    print("\n=== Database Example ===")

    # Get database instance
    db = get_database()

    # Create a playlist
    playlist = Playlist(
        id='example_123',
        name='Example Playlist',
        url='https://example.com/playlist/123',
        owner='user',
        tracks_count=10,
        service='spotify'
    )

    # Add to database
    db.add_playlist(playlist.to_dict(), 'spotify')
    print(f"✓ Added playlist: {playlist.name}")

    # Get playlists
    playlists = db.get_playlists(service='spotify')
    print(f"✓ Found {len(playlists)} playlists")

    # Clean up
    db.delete_playlist('example_123')


def example_cache():
    """Cache management example."""
    from music_tools_common.database import get_cache

    print("\n=== Cache Example ===")

    # Get cache instance with 1 hour TTL
    cache = get_cache(ttl=3600)

    # Set cache value
    cache.set('user_data', {
        'id': '123',
        'name': 'Example User',
        'preferences': {'theme': 'dark'}
    })
    print("✓ Cached user data")

    # Get cache value
    user_data = cache.get('user_data')
    print(f"✓ Retrieved from cache: {user_data['name']}")

    # Clear cache
    cache.delete('user_data')
    print("✓ Cleared cache")


def example_auth():
    """Authentication example."""
    from music_tools_common.auth import get_spotify_client

    print("\n=== Authentication Example ===")

    try:
        # Get authenticated Spotify client
        sp = get_spotify_client()

        # Get user info
        user = sp.me()
        print(f"✓ Authenticated as: {user['id']}")

    except Exception as e:
        print(f"Authentication failed: {e}")
        print("Make sure SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET are set")


def example_cli():
    """CLI framework example."""
    from music_tools_common.cli import BaseCLI, InteractiveMenu

    print("\n=== CLI Example ===")

    class ExampleApp(BaseCLI):
        def run(self) -> int:
            menu = InteractiveMenu("Example Application")
            menu.add_option("Show info", self.show_info)
            menu.add_option("Process data", self.process_data)

            print("\nStarting menu (enter 0 to exit)...")
            # Don't actually run the menu in this example
            # menu.run()

            return 0

        def show_info(self):
            self.info("Application info displayed")

        def process_data(self):
            self.info("Processing data...")

    app = ExampleApp("example-app", "1.0.0")
    print(f"✓ Created CLI app: {app.name} v{app.version}")


def example_utils():
    """Utilities example."""
    import os
    import tempfile

    from music_tools_common.utils import retry, validate_email, validate_url
    from music_tools_common.utils.file import safe_read_json, safe_write_json

    print("\n=== Utils Example ===")

    # Retry decorator
    @retry(max_attempts=3, delay=0.1)
    def flaky_function():
        import random
        if random.random() < 0.3:  # 30% success rate
            return "Success!"
        raise Exception("Failed")

    print("Testing retry logic...")
    # Note: This might fail, that's okay for demo

    # Validation
    print(f"✓ Email valid: {validate_email('user@example.com')}")
    print(f"✓ URL valid: {validate_url('https://example.com')}")

    # File operations
    test_file = os.path.join(tempfile.gettempdir(), 'test.json')
    data = {'example': 'data', 'numbers': [1, 2, 3]}

    safe_write_json(data, test_file)
    print(f"✓ Wrote JSON to {test_file}")

    loaded_data = safe_read_json(test_file)
    print(f"✓ Read JSON: {loaded_data}")

    os.remove(test_file)


def example_metadata():
    """Metadata handling example."""
    from music_tools_common.metadata import MetadataReader, MetadataWriter

    print("\n=== Metadata Example ===")

    print("Metadata reader and writer are available for:")
    print("- Reading music file metadata (MP3, FLAC, etc.)")
    print("- Writing/updating metadata tags")
    print("\nExample:")
    print("  reader = MetadataReader()")
    print("  metadata = reader.read('song.mp3')")
    print("  writer = MetadataWriter()")
    print("  writer.write('song.mp3', {'artist': 'New Artist'})")


def main():
    """Run all examples."""
    print("Music Tools Common - Usage Examples")
    print("=" * 50)

    example_config()
    example_database()
    example_cache()
    # example_auth()  # Commented out as it requires actual credentials
    example_cli()
    example_utils()
    example_metadata()

    print("\n" + "=" * 50)
    print("Examples completed!")


if __name__ == '__main__':
    main()
