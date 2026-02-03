#!/usr/bin/env python3
"""
Complete Application Example

Demonstrates a full CLI application using the framework.
"""

import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from music_tools_common.cli import BaseCLI, InteractiveMenu, ProgressTracker
from music_tools_common.cli.prompts import prompt_user, prompt_choice
from music_tools_common.cli.output import (
    print_success,
    print_error,
    print_warning,
    print_table,
)


class MyMusicTool(BaseCLI):
    """Example music tool CLI application."""

    def run(self) -> int:
        """Run the main application."""
        # Create main menu
        menu = InteractiveMenu("My Music Tool")

        # Add menu options
        menu.add_option("Process Files", self.process_files)
        menu.add_option("View Statistics", self.view_statistics)
        menu.add_option("Settings", self.show_settings)

        # Run menu
        menu.run()

        return 0

    def process_files(self):
        """Process files with progress tracking."""
        print("\n" + "=" * 60)
        print("FILE PROCESSING")
        print("=" * 60)

        # Get user input
        file_count = input("\nHow many files to process? [10]: ").strip()
        file_count = int(file_count) if file_count else 10

        # Process with progress bar
        print(f"\nProcessing {file_count} files...\n")

        with ProgressTracker(total=file_count, desc="Processing files") as progress:
            for i in range(file_count):
                time.sleep(0.1)  # Simulate work
                progress.update(1)

        print_success(f"Processed {file_count} files successfully!")
        input("\nPress Enter to continue...")

    def view_statistics(self):
        """Display statistics table."""
        print("\n" + "=" * 60)
        print("STATISTICS")
        print("=" * 60 + "\n")

        # Sample data
        stats = [
            {"Metric": "Files Processed", "Value": "1,234"},
            {"Metric": "Total Size", "Value": "45.6 GB"},
            {"Metric": "Processing Time", "Value": "2h 15m"},
            {"Metric": "Success Rate", "Value": "98.5%"},
        ]

        print_table(stats, title="Processing Statistics")

        input("\nPress Enter to continue...")

    def show_settings(self):
        """Show settings submenu."""
        settings_menu = InteractiveMenu("Settings")

        settings_menu.add_option("Change Output Directory", self.change_output_dir)
        settings_menu.add_option("Configure API Keys", self.configure_api)
        settings_menu.add_option("Reset to Defaults", self.reset_settings)

        settings_menu.run()

    def change_output_dir(self):
        """Change output directory."""
        print("\n" + "=" * 60)
        print("CHANGE OUTPUT DIRECTORY")
        print("=" * 60 + "\n")

        current = "/home/user/music/output"
        print(f"Current directory: {current}")

        new_dir = prompt_user("\nEnter new directory", default=current)
        print_success(f"Output directory changed to: {new_dir}")

        input("\nPress Enter to continue...")

    def configure_api(self):
        """Configure API keys."""
        print("\n" + "=" * 60)
        print("CONFIGURE API KEYS")
        print("=" * 60 + "\n")

        print_warning("API configuration not yet implemented")
        input("\nPress Enter to continue...")

    def reset_settings(self):
        """Reset settings to defaults."""
        print("\n" + "=" * 60)
        print("RESET SETTINGS")
        print("=" * 60 + "\n")

        confirm = prompt_choice(
            "Are you sure you want to reset all settings?",
            ["Yes, reset", "No, cancel"]
        )

        if confirm == "Yes, reset":
            print_success("Settings reset to defaults")
        else:
            print_warning("Reset cancelled")

        input("\nPress Enter to continue...")


def main():
    """Main entry point."""
    app = MyMusicTool("my-music-tool", "1.0.0")

    try:
        return app.run()
    except KeyboardInterrupt:
        print("\n\nExiting...")
        return 0
    except Exception as e:
        app.error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
