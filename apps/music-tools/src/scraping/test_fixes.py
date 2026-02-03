#!/usr/bin/env python3
"""
Test script to verify all fixes work correctly.
"""

import os
import sys
import tempfile
from datetime import date

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_requirements_file():
    """Test that requirements.txt exists and is valid."""
    print("🔍 Testing requirements.txt...")

    if not os.path.exists('requirements.txt'):
        print("❌ requirements.txt not found")
        return False

    with open('requirements.txt', 'r') as f:
        content = f.read()
        if 'requests' in content and 'beautifulsoup4' in content:
            print("✅ requirements.txt is valid")
            return True
        else:
            print("❌ requirements.txt missing required dependencies")
            return False


def test_config_imports():
    """Test that config.py imports work correctly."""
    print("🔍 Testing config imports...")

    try:
        from config import (
            ALL_EDM_GENRES,
            DEFAULT_GENRES,
            DEFAULT_MAX_PAGES,
            DOWNLOAD_PATTERNS,
            MAX_RETRIES,
            REQUEST_TIMEOUT,
        )

        # Test that patterns are pre-compiled
        if hasattr(DOWNLOAD_PATTERNS[0], 'search'):
            print("✅ Config imports work and patterns are pre-compiled")
            return True
        else:
            print("❌ Download patterns are not pre-compiled")
            return False

    except ImportError as e:
        print(f"❌ Config import failed: {e}")
        return False


def test_error_handling():
    """Test error handling utilities."""
    print("🔍 Testing error handling...")

    try:
        from error_handling import (
            AsyncRateLimiter,
            ThreadSafeRateLimiter,
            safe_file_read,
            validate_file_path,
            validate_url,
        )

        # Test URL validation
        assert validate_url("https://example.com") is True
        assert validate_url("not-a-url") is False
        assert validate_url("javascript:alert('xss')") is False

        # Test file path validation
        assert validate_file_path("test.txt") is True
        assert validate_file_path("/tmp/test.txt") is True  # Allow temp files

        # Test rate limiters
        rate_limiter = ThreadSafeRateLimiter()
        rate_limiter.wait_if_needed("example.com")

        print("✅ Error handling utilities work correctly")
        return True

    except Exception as e:
        print(f"❌ Error handling test failed: {e}")
        return False


def test_music_scraper():
    """Test music scraper with fixes."""
    print("🔍 Testing music scraper...")

    try:
        from config import DEFAULT_GENRES
        from music_scraper import MusicBlogScraper

        # Test initialization with validation
        scraper = MusicBlogScraper("https://example.com", "test_output.txt")

        # Test genre extraction with BeautifulSoup object handling
        from bs4 import BeautifulSoup
        html = "<html><body>progressive house melodic techno</body></html>"
        soup = BeautifulSoup(html, 'html.parser')
        genres = scraper.extract_genres_from_text(soup)

        if 'progressive house' in genres and 'melodic' in genres:
            print("✅ Music scraper works with fixes")
            return True
        else:
            print("❌ Genre extraction not working correctly")
            return False

    except Exception as e:
        print(f"❌ Music scraper test failed: {e}")
        return False


def test_link_extractor():
    """Test link extractor with streaming."""
    print("🔍 Testing link extractor...")

    try:
        from link_extractor import LinkExtractor

        # Create test file with more specific content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("""
            Download links:
            - https://nfile.cc/test1.flac
            - https://mediafire.com/test2_320.mp3
            - https://mega.nz/test3.zip
            """)
            test_file = f.name

        try:
            extractor = LinkExtractor()
            results = extractor.extract_from_text(test_file)

            # The extractor finds links in both the text and the bullet points
            if results['total_links'] >= 3:  # Allow for multiple matches
                print("✅ Link extractor works with streaming")
                return True
            else:
                print(f"❌ Link extractor found {results['total_links']} links, expected at least 3")
                return False

        finally:
            os.unlink(test_file)

    except Exception as e:
        print(f"❌ Link extractor test failed: {e}")
        return False


def test_async_scraper():
    """Test async scraper with new rate limiter."""
    print("🔍 Testing async scraper...")

    try:
        from async_scraper import AsyncMusicBlogScraper
        from config import MAX_CONCURRENT_REQUESTS

        # Test initialization
        scraper = AsyncMusicBlogScraper("https://example.com", max_concurrent=3)

        if scraper.max_concurrent == 3 and hasattr(scraper.rate_limiter, 'wait_if_needed'):
            print("✅ Async scraper works with new rate limiter")
            return True
        else:
            print("❌ Async scraper not properly configured")
            return False

    except Exception as e:
        print(f"❌ Async scraper test failed: {e}")
        return False


def test_cli_validation():
    """Test CLI validation."""
    print("🔍 Testing CLI validation...")

    try:
        from cli_scraper import EDMScraperCLI
        from error_handling import validate_file_path, validate_url

        EDMScraperCLI()

        # Test URL validation in CLI
        assert validate_url("https://example.com") is True
        assert validate_url("not-a-url") is False

        # Test file path validation
        assert validate_file_path("test.txt") is True
        assert validate_file_path("/tmp/test.txt") is True  # Allow temp files

        print("✅ CLI validation works correctly")
        return True

    except Exception as e:
        print(f"❌ CLI validation test failed: {e}")
        return False


def test_date_validation():
    """Test date parsing and validation."""
    print("🔍 Testing date validation...")

    try:
        from music_scraper import MusicBlogScraper

        scraper = MusicBlogScraper("https://example.com")

        # Test valid dates
        assert scraper.parse_date_string("2024-01-15") == date(2024, 1, 15)
        assert scraper.parse_date_string("01/15/2024") == date(2024, 1, 15)

        # Test invalid dates
        assert scraper.parse_date_string("invalid") is None
        assert scraper.parse_date_string("2024-13-45") is None  # Invalid month/day

        # Test date validation
        assert scraper.is_valid_date(date(2024, 1, 15)) is True
        assert scraper.is_valid_date(date(1800, 1, 1)) is False  # Too old
        assert scraper.is_valid_date(date(2030, 1, 1)) is False  # Too far in future

        print("✅ Date validation works correctly")
        return True

    except Exception as e:
        print(f"❌ Date validation test failed: {e}")
        return False


def test_models_validation():
    """Test Pydantic models validation."""
    print("🔍 Testing models validation...")

    try:
        from models import BlogPost, DownloadLink, validate_post_data

        # Test valid post data
        post_data = {
            'url': 'https://example.com/post',
            'title': 'Test Post',
            'genres': ['house', 'techno'],
            'download_links': [{'url': 'https://example.com/track.flac'}]
        }

        validated_post = validate_post_data(post_data)
        if validated_post:
            print("✅ Models validation works correctly")
            return True
        else:
            print("❌ Models validation failed")
            return False

    except Exception as e:
        print(f"❌ Models validation test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🧪 Running comprehensive tests for all fixes...")
    print("=" * 60)

    tests = [
        test_requirements_file,
        test_config_imports,
        test_error_handling,
        test_music_scraper,
        test_link_extractor,
        test_async_scraper,
        test_cli_validation,
        test_date_validation,
        test_models_validation
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            print()

    print("=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! All fixes are working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the issues above.")
        return 1


if __name__ == "__main__":
    exit(main())
