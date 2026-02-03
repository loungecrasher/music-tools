#!/usr/bin/env python3
"""
Example CLI application using music_tools_common.
"""
from music_tools_common.cli import BaseCLI, InteractiveMenu, ProgressTracker
from music_tools_common.config import config_manager
from music_tools_common.database import get_database
from music_tools_common.utils import retry
import time


class MusicToolsApp(BaseCLI):
    """Example Music Tools CLI application."""
    
    def __init__(self):
        super().__init__("music-tools-example", "1.0.0")
        self.db = get_database()
    
    def run(self) -> int:
        """Run the application."""
        self.info(f"Starting {self.name} v{self.version}")
        
        menu = InteractiveMenu("Music Tools Example")
        menu.add_option("View Configuration", self.view_config)
        menu.add_option("List Playlists", self.list_playlists)
        menu.add_option("Process Data (with progress)", self.process_with_progress)
        menu.add_option("Test Retry Logic", self.test_retry)
        
        menu.run()
        
        return 0
    
    def view_config(self):
        """View current configuration."""
        print("\nCurrent Configuration:")
        print("-" * 40)
        
        # Load Spotify config
        spotify_config = config_manager.load_config('spotify')
        print(f"Spotify Client ID: {spotify_config.get('client_id', 'Not set')[:10]}...")
        print(f"Redirect URI: {spotify_config.get('redirect_uri', 'Not set')}")
        
        # Validate
        errors = config_manager.validate_config('spotify')
        if errors:
            print(f"\n⚠ Configuration errors: {errors}")
        else:
            print("\n✓ Configuration is valid")
    
    def list_playlists(self):
        """List all playlists in database."""
        print("\nPlaylists in Database:")
        print("-" * 40)
        
        playlists = self.db.get_playlists()
        
        if not playlists:
            print("No playlists found")
            return
        
        for playlist in playlists:
            print(f"• {playlist['name']} ({playlist['tracks_count']} tracks)")
    
    def process_with_progress(self):
        """Example of processing with progress bar."""
        print("\nProcessing data...")
        
        items = list(range(100))
        
        with ProgressTracker(total=len(items), desc="Processing") as progress:
            for item in items:
                # Simulate processing
                time.sleep(0.01)
                progress.update(1)
        
        print("✓ Processing complete!")
    
    def test_retry(self):
        """Test retry logic."""
        print("\nTesting retry logic...")
        
        @retry(max_attempts=3, delay=0.5)
        def flaky_operation():
            import random
            if random.random() < 0.5:
                raise Exception("Simulated failure")
            return "Success!"
        
        try:
            result = flaky_operation()
            print(f"✓ {result}")
        except Exception as e:
            print(f"✗ Failed after retries: {e}")


def main():
    """Main entry point."""
    app = MusicToolsApp()
    return app.run()


if __name__ == '__main__':
    exit(main())
