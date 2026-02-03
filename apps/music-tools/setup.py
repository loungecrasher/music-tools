#!/usr/bin/env python3
"""
Setup script for Music Tools.
Helps users set up the project for the first time.
"""
import argparse
import json
import os
import subprocess
import sys


def check_python_version() -> bool:
    """Check if Python version is 3.8 or higher.

    Returns:
        True if Python version is 3.8 or higher, False otherwise
    """
    major = sys.version_info.major
    minor = sys.version_info.minor
    if major < 3 or (major == 3 and minor < 8):
        print(f"Error: Python 3.8 or higher is required. You have {sys.version}")
        return False

    print(f"Python version: {sys.version}")
    return True


def install_dependencies(upgrade: bool = False) -> bool:
    """Install dependencies from requirements.txt.

    Args:
        upgrade: Whether to upgrade existing packages

    Returns:
        True if successful, False otherwise
    """
    try:
        cmd = [sys.executable, "-m", "pip", "install"]

        if upgrade:
            cmd.append("--upgrade")

        cmd.extend(["-r", "requirements.txt"])

        print("Installing dependencies...")
        subprocess.check_call(cmd)

        print("Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error installing dependencies: {e}")
        return False


def create_directories() -> bool:
    """Create required directories.

    Returns:
        True if successful, False otherwise
    """
    try:
        directories = [
            "config",
            "data"
        ]

        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            print(f"Created directory: {directory}")

        return True
    except Exception as e:
        print(f"Error creating directories: {e}")
        return False


def create_config_files() -> bool:
    """Create empty configuration files.

    Returns:
        True if successful, False otherwise
    """
    try:
        config_files = {
            "config/spotify_config.json": {
                "client_id": "",
                "client_secret": "",
                "redirect_uri": "http://localhost:8888/callback"
            },
            "config/deezer_config.json": {
                "email": ""
            }
        }

        for file_path, content in config_files.items():
            # Skip if file already exists
            if os.path.exists(file_path):
                print(f"Config file already exists: {file_path}")
                continue

            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            # Write file
            with open(file_path, 'w') as f:
                json.dump(content, f, indent=2)

            # Set secure permissions
            os.chmod(file_path, 0o600)

            print(f"Created config file: {file_path}")

        return True
    except Exception as e:
        print(f"Error creating config files: {e}")
        return False


def run_tests() -> bool:
    """Run basic tests to verify setup.

    Returns:
        True if successful, False otherwise
    """
    try:
        # Check if core modules can be imported
        print("Testing core module imports...")

        try:
            sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
            # Add packages directory to path (music_tools_common is a symlink to packages/common)
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', '..', 'packages'))
            from music_tools_common import get_database
            get_database()
            print("Core modules imported successfully")
        except ImportError as e:
            print(f"Error importing core modules: {e}")
            return False

        # Check if database can be initialized
        print("Testing database initialization...")

        try:
            db_path = os.path.join("data", "music_tools.db")
            if os.path.exists(db_path):
                print(f"Database already exists at: {db_path}")
            else:
                # Database will be created when db is accessed
                print(f"Database will be created at: {db_path}")
        except Exception as e:
            print(f"Error checking database: {e}")
            return False

        print("All tests passed")
        return True
    except Exception as e:
        print(f"Error running tests: {e}")
        return False


def main() -> None:
    """Main function."""
    parser = argparse.ArgumentParser(description="Set up Music Tools")
    parser.add_argument("--upgrade", action="store_true", help="Upgrade existing packages")
    parser.add_argument("--skip-deps", action="store_true", help="Skip dependency installation")
    parser.add_argument("--skip-tests", action="store_true", help="Skip tests")

    args = parser.parse_args()

    print("\n=== Music Tools Setup ===\n")

    # Check Python version
    if not check_python_version():
        sys.exit(1)

    # Create directories
    if not create_directories():
        sys.exit(1)

    # Create config files
    if not create_config_files():
        sys.exit(1)

    # Install dependencies
    if not args.skip_deps:
        if not install_dependencies(args.upgrade):
            sys.exit(1)
    else:
        print("Skipping dependency installation")

    # Run tests
    if not args.skip_tests:
        if not run_tests():
            sys.exit(1)
    else:
        print("Skipping tests")

    print("\nSetup completed successfully!")
    print("\nYou can now run the application with:")
    print("  python -m music_tools_cli --help")
    print("  python -m music_tools_cli menu  # Legacy Rich UI")
    print("\nOr migrate existing data with:")
    print("  python migrate_data.py")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nSetup interrupted")
        sys.exit(0)
    except Exception as e:
        print(f"\nAn unexpected error occurred: {str(e)}")
        sys.exit(1)
