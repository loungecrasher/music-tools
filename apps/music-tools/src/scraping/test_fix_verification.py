
import os
import sys

# Add apps/music-tools/src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from scraping.async_scraper import AsyncMusicBlogScraper
from scraping.music_scraper import MusicBlogScraper


def test_sync_scraper():
    print("Testing MusicBlogScraper.scrape_website...")
    scraper = MusicBlogScraper("https://example.com")
    if hasattr(scraper, 'scrape_website'):
        print("✅ MusicBlogScraper has scrape_website method")
    else:
        print("❌ MusicBlogScraper MISSING scrape_website method")
        return False

    # We won't actually scrape to avoid network calls/time, just checking existence is enough for the reported error
    return True


def test_async_scraper():
    print("\nTesting AsyncMusicBlogScraper.scrape_website...")
    scraper = AsyncMusicBlogScraper("https://example.com")
    if hasattr(scraper, 'scrape_website'):
        print("✅ AsyncMusicBlogScraper has scrape_website method")
    else:
        print("❌ AsyncMusicBlogScraper MISSING scrape_website method")
        return False
    return True


if __name__ == "__main__":
    sync_ok = test_sync_scraper()
    async_ok = test_async_scraper()

    if sync_ok and async_ok:
        print("\n✅ Verification Successful: Both scrapers have the required method.")
        sys.exit(0)
    else:
        print("\n❌ Verification Failed.")
        sys.exit(1)
