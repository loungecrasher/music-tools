"""
EDM blog scraping module for Music Tools.

This module provides functionality to scrape EDM music blogs for download links,
genre information, and track metadata.
"""

from .cli_scraper import main as cli_main
from .music_scraper import MusicBlogScraper
from .link_extractor import LinkExtractor

__all__ = [
    'cli_main',
    'MusicBlogScraper',
    'LinkExtractor',
]
