#!/usr/bin/env python3
"""
Progress Bar Demo

Demonstrates progress tracking with the CLI framework.
"""

import sys
import time
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from music_tools_common.cli import ProgressTracker
from music_tools_common.cli.output import print_success


def main():
    """Main function demonstrating progress tracking."""
    total_items = 100

    print("\nProcessing items with progress bar...\n")

    # Use progress tracker
    with ProgressTracker(total=total_items, desc="Processing") as progress:
        for i in range(total_items):
            # Simulate some work
            time.sleep(0.05)

            # Update progress
            progress.update(1)

    print_success(f"Processed {total_items} items successfully!")


if __name__ == "__main__":
    main()
