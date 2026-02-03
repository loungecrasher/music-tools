#!/usr/bin/env python3
"""
Basic Menu Example

Demonstrates how to create a simple interactive menu using the CLI framework.
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from music_tools_common.cli import InteractiveMenu
from music_tools_common.cli.output import print_info, print_success


def option1_handler():
    """Handler for option 1."""
    print_info("You selected option 1", "Option 1")
    input("\nPress Enter to continue...")


def option2_handler():
    """Handler for option 2."""
    print_info("You selected option 2", "Option 2")
    input("\nPress Enter to continue...")


def option3_handler():
    """Handler for option 3."""
    print_success("You selected option 3", "Option 3")
    input("\nPress Enter to continue...")


def main():
    """Main function demonstrating basic menu usage."""
    # Create menu
    menu = InteractiveMenu("Main Menu")

    # Add options
    menu.add_option("First Option", option1_handler)
    menu.add_option("Second Option", option2_handler)
    menu.add_option("Third Option", option3_handler)

    # Run menu
    menu.run()


if __name__ == "__main__":
    main()
