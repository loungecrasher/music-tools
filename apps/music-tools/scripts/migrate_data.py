#!/usr/bin/env python3
"""
Data migration script for Music Tools.
Migrates data from JSON files to SQLite database.
"""
import os
import sys
import json
import argparse
from typing import Dict, List, Any, Tuple

# Add the current directory and packages to the Python path
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
# Add packages directory to path (music_tools_common is a symlink to packages/common)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', '..', 'packages'))

# Import core modules
try:
    from music_tools_common import (
        get_database,
        setup_logger
    )
    # Initialize database instance
    db = get_database()

    # Define confirm_action function (simple implementation)
    def confirm_action(prompt: str, default: bool = False) -> bool:
        """Ask user for confirmation."""
        suffix = " [Y/n]: " if default else " [y/N]: "
        response = input(prompt + suffix).strip().lower()
        if not response:
            return default
        return response in ['y', 'yes']
except ImportError as e:
    print(f"Error: Core modules not found. Please ensure music_tools_common is installed: {e}")
    sys.exit(1)

# Set up logging
logger = setup_logger('music_tools.migrate')

def migrate_spotify_playlists(json_file: str) -> Tuple[int, int]:
    """Migrate Spotify playlists from JSON file to database.
    
    Args:
        json_file: Path to JSON file
        
    Returns:
        Tuple of (success_count, error_count)
    """
    if not os.path.exists(json_file):
        print(f"Error: File not found: {json_file}")
        return (0, 0)
    
    print(f"Migrating Spotify playlists from {json_file}...")
    
    try:
        # Import playlists
        success, error = db.import_json_playlists(json_file, 'spotify')
        
        print(f"Migration completed:")
        print(f"  - Successfully migrated: {success} playlists")
        print(f"  - Failed to migrate: {error} playlists")
        
        return (success, error)
    except Exception as e:
        print(f"Error migrating playlists: {str(e)}")
        return (0, 0)

def find_json_files() -> List[str]:
    """Find JSON files in the project directory.
    
    Returns:
        List of JSON file paths
    """
    json_files = []
    
    # Check common locations
    locations = [
        "Spotify Script/V2/playlist_database.json",
        "config/spotify_config.json",
        "config/deezer_config.json"
    ]
    
    for location in locations:
        if os.path.exists(location):
            json_files.append(location)
    
    return json_files

def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(description="Migrate data from JSON files to SQLite database")
    parser.add_argument("--file", help="Path to JSON file to migrate")
    parser.add_argument("--service", choices=["spotify", "deezer"], help="Service to migrate data for")
    parser.add_argument("--auto", action="store_true", help="Automatically migrate all found files")
    
    args = parser.parse_args()
    
    print("\n=== Music Tools Data Migration ===\n")
    
    if args.file:
        # Migrate specific file
        if not args.service:
            print("Error: --service is required when specifying a file")
            sys.exit(1)
            
        if args.service == "spotify":
            migrate_spotify_playlists(args.file)
        else:
            print(f"Migration for {args.service} is not yet implemented")
    elif args.auto:
        # Auto-migrate all found files
        json_files = find_json_files()
        
        if not json_files:
            print("No JSON files found to migrate")
            return
            
        print(f"Found {len(json_files)} JSON files:")
        for i, file in enumerate(json_files, 1):
            print(f"{i}. {file}")
            
        confirm = confirm_action("\nMigrate all these files?", False)
        if not confirm:
            print("Migration cancelled")
            return
            
        for file in json_files:
            if "spotify" in file.lower():
                migrate_spotify_playlists(file)
            else:
                print(f"Skipping {file} (unsupported format)")
    else:
        # Interactive mode
        json_files = find_json_files()
        
        if not json_files:
            print("No JSON files found to migrate")
            
            # Prompt for manual file path
            file_path = input("\nEnter path to JSON file to migrate (or leave blank to cancel): ").strip()
            if not file_path:
                print("Migration cancelled")
                return
                
            if not os.path.exists(file_path):
                print(f"Error: File not found: {file_path}")
                return
                
            service = input("Enter service (spotify/deezer): ").strip().lower()
            if service == "spotify":
                migrate_spotify_playlists(file_path)
            elif service == "deezer":
                print("Migration for Deezer is not yet implemented")
            else:
                print(f"Error: Unsupported service: {service}")
            
            return
            
        print(f"Found {len(json_files)} JSON files:")
        for i, file in enumerate(json_files, 1):
            print(f"{i}. {file}")
            
        choice = input("\nEnter file number to migrate (or 'a' for all): ").strip()
        
        if choice.lower() == 'a':
            # Migrate all files
            for file in json_files:
                if "spotify" in file.lower():
                    migrate_spotify_playlists(file)
                else:
                    print(f"Skipping {file} (unsupported format)")
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(json_files):
                    file = json_files[idx]
                    
                    if "spotify" in file.lower():
                        migrate_spotify_playlists(file)
                    else:
                        print(f"Migration for {file} is not yet implemented")
                else:
                    print("Invalid choice")
            except ValueError:
                print("Invalid input")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nMigration interrupted")
        sys.exit(0)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {str(e)}")
        sys.exit(1)
