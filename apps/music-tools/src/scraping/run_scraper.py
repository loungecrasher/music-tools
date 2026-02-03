#!/usr/bin/env python3
"""
EDM Music Blog Scraper - Launcher
Simple launcher script for the interactive CLI.
"""


def main():
    """Launch the appropriate scraper based on arguments."""

    # Check if CLI module exists
    try:
        from cli_scraper import main as cli_main
    except ImportError:
        print("Error: CLI module not found. Make sure cli_scraper.py is in the same directory.")
        return

    # Check if required dependencies are installed
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        print("Error: Required dependencies not installed.")
        print("Please run: pip install -r requirements.txt")
        return

    # Launch the CLI
    cli_main()


if __name__ == "__main__":
    main()
