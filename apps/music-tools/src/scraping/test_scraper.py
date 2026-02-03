#!/usr/bin/env python3
"""
import time
Pytest test suite for the EDM Music Blog Scraper.
"""

import json
import os
from datetime import date
from unittest.mock import MagicMock, Mock, patch

import pytest
from bs4 import BeautifulSoup

from .async_scraper import AsyncMusicBlogScraper
from .error_handling import (
    create_resilient_session,
    exponential_backoff,
    rate_limit_handler,
    validate_url,
)
from .link_extractor import LinkExtractor
from .models import (
    BlogPost,
    DownloadLink,
    Genre,
    LinkExtractionResult,
    ScraperConfig,
    ScraperResult,
    validate_post_data,
)

# Import modules to test
from .music_scraper import MusicBlogScraper
from .preferred_genres_scraper import PreferredGenresScraper


# Fixtures
@pytest.fixture
def sample_html():
    """Sample HTML content for testing."""
    return """
    <html>
    <head><title>Test Blog Post</title></head>
    <body>
        <article>
            <h1>Progressive House Mix 2024</h1>
            <div class="post-date">2024-01-15</div>
            <div class="genres">Genre: Progressive House, Melodic</div>
            <div class="content">
                <p>Download in FLAC: <a href="https://nfile.cc/track123.flac">Download FLAC</a></p>
                <p>Download in MP3 320: <a href="https://mediafire.com/track123_320.mp3">Download MP3</a></p>
            </div>
        </article>
    </body>
    </html>
    """


@pytest.fixture
def sample_blog_posts_html():
    """Sample HTML with multiple blog post links."""
    return """
    <html>
    <body>
        <div class="posts">
            <a href="/date/2024/01/15/progressive-house-mix/">Progressive House Mix</a>
            <a href="/djs-chart/techno-classics/">Techno Classics</a>
            <a href="/house/deep-vibes/">Deep House Vibes</a>
        </div>
    </body>
    </html>
    """


@pytest.fixture
def scraper():
    """Create a MusicBlogScraper instance."""
    return MusicBlogScraper("https://example.com", "test_output.txt")


@pytest.fixture
def preferred_scraper():
    """Create a PreferredGenresScraper instance."""
    return PreferredGenresScraper("https://example.com", "test_preferred.txt")


@pytest.fixture
def link_extractor():
    """Create a LinkExtractor instance."""
    return LinkExtractor()


@pytest.fixture
def sample_json_data():
    """Sample JSON data for testing."""
    return {
        "metadata": {"generated_at": "2024-01-15T10:00:00", "total_posts": 2},
        "posts": [
            {
                "url": "https://example.com/post1",
                "title": "Test Post 1",
                "genres": ["house", "progressive"],
                "download_links": [
                    "https://nfile.cc/file1.flac",
                    "https://mediafire.com/file1_320.mp3",
                ],
            },
            {
                "url": "https://example.com/post2",
                "title": "Test Post 2",
                "genres": ["techno"],
                "download_links": ["https://mega.nz/file2.zip"],
            },
        ],
    }


class TestMusicBlogScraper:
    """Test cases for MusicBlogScraper class."""

    def test_initialization(self, scraper):
        """Test scraper initialization."""
        assert scraper.base_url == "https://example.com"
        assert scraper.output_file == "test_output.txt"
        assert len(scraper.download_patterns) > 0

    @patch("music_scraper.safe_request")
    @patch("music_scraper.parse_content_safely")
    def test_get_page_content_success(self, mock_parse, mock_request, scraper, sample_html):
        """Test successful page content retrieval."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        mock_parse.return_value = BeautifulSoup(sample_html, "html.parser")

        result = scraper.get_page_content("https://example.com/post")

        assert result is not None
        assert isinstance(result, BeautifulSoup)
        mock_request.assert_called_once()
        mock_parse.assert_called_once()

    def test_is_blog_post_url(self, scraper):
        """Test blog post URL detection."""
        # Valid post URLs
        assert scraper.is_blog_post_url("/date/2024/01/15/test-post/")
        assert scraper.is_blog_post_url("/djs-chart/house-mix/")
        assert scraper.is_blog_post_url("/house/deep-vibes/")
        assert scraper.is_blog_post_url("/2024/01/test-post/")

        # Invalid URLs
        assert not scraper.is_blog_post_url("/tag/house/")
        assert not scraper.is_blog_post_url("/category/music/")
        assert not scraper.is_blog_post_url("/wp-admin/")
        assert not scraper.is_blog_post_url("/style.css")

    def test_extract_genres_from_text(self, scraper):
        """Test genre extraction from text."""
        text = "This is a Progressive House and Melodic Techno mix with some Deep House vibes"
        genres = scraper.extract_genres_from_text(text)

        assert "progressive house" in genres
        assert "melodic" in genres
        assert "techno" in genres
        assert "deep house" in genres

    def test_extract_download_links(self, scraper, sample_html):
        """Test download link extraction."""
        soup = BeautifulSoup(sample_html, "html.parser")
        links = scraper.extract_download_links(soup, "https://example.com/post")

        assert len(links) == 2
        assert any("flac" in link.lower() for link in links)
        assert any("mp3" in link.lower() for link in links)

    def test_extract_post_date(self, scraper, sample_html):
        """Test post date extraction."""
        soup = BeautifulSoup(sample_html, "html.parser")
        post_date = scraper.extract_post_date(soup, "https://example.com/post")

        assert post_date == date(2024, 1, 15)

    def test_extract_post_date_from_url(self, scraper):
        """Test date extraction from URL patterns."""
        # Test various URL date patterns
        assert scraper.extract_date_from_url("/2024/01/15/post/") == date(2024, 1, 15)
        assert scraper.extract_date_from_url("/2024-01-15/post/") == date(2024, 1, 15)
        assert scraper.extract_date_from_url("/2024_01_15/post/") == date(2024, 1, 15)

    def test_parse_date_string(self, scraper):
        """Test date string parsing."""
        # Test various date formats
        assert scraper.parse_date_string("2024-01-15") == date(2024, 1, 15)
        assert scraper.parse_date_string("01/15/2024") == date(2024, 1, 15)
        assert scraper.parse_date_string("January 15, 2024") == date(2024, 1, 15)
        assert scraper.parse_date_string("15 Jan 2024") == date(2024, 1, 15)
        assert scraper.parse_date_string("invalid date") is None

    @patch("music_scraper.MusicBlogScraper.get_page_content")
    def test_filter_posts_by_genre(self, mock_get_page, scraper, sample_html):
        """Test filtering posts by genre."""
        mock_get_page.return_value = BeautifulSoup(sample_html, "html.parser")

        post_urls = ["https://example.com/post1"]
        target_genres = ["progressive house", "melodic"]

        results = scraper.filter_posts_by_genre(post_urls, target_genres)

        assert len(results) == 1
        assert results[0]["title"] == "Progressive House Mix 2024"
        assert "progressive house" in results[0]["matching_genres"]
        assert len(results[0]["download_links"]) == 2

    def test_save_results(self, scraper, tmp_path):
        """Test saving results to file."""
        scraper.output_file = str(tmp_path / "test_output.txt")

        matching_posts = [
            {
                "url": "https://example.com/post1",
                "title": "Test Post",
                "genres": ["house", "progressive"],
                "matching_genres": ["house"],
                "download_links": ["https://example.com/download.mp3"],
                "post_date": date(2024, 1, 15),
            }
        ]

        scraper.save_results(matching_posts)

        assert os.path.exists(scraper.output_file)
        with open(scraper.output_file, "r") as f:
            content = f.read()
            assert "Test Post" in content
            assert "https://example.com/download.mp3" in content


class TestPreferredGenresScraper:
    """Test cases for PreferredGenresScraper class."""

    def test_initialization(self, preferred_scraper):
        """Test preferred genres scraper initialization."""
        assert len(preferred_scraper.preferred_genres) > 0
        assert "house" in preferred_scraper.preferred_genres
        assert preferred_scraper.preferred_genres["house"] == 10

    def test_calculate_post_score(self, preferred_scraper):
        """Test post scoring calculation."""
        post_info = {
            "matching_genres": ["house", "progressive house"],
            "download_links": [
                "https://example.com/track.flac",
                "https://example.com/track_320.mp3",
            ],
        }

        score = preferred_scraper.calculate_post_score(post_info)

        # house (10) + progressive house (10) + 2 links (4) + 1 FLAC (3) = 27
        assert score == 27

    def test_genre_extraction_with_aliases(self, preferred_scraper):
        """Test genre extraction with aliases."""
        text = "This is a prog house mix with some dnb elements"
        genres = preferred_scraper.extract_genres_from_text(text)

        assert "progressive house" in genres  # Should match 'prog house' alias
        assert "drum and bass" in genres  # Should match 'dnb' alias


class TestLinkExtractor:
    """Test cases for LinkExtractor class."""

    def test_initialization(self, link_extractor):
        """Test link extractor initialization."""
        assert len(link_extractor.download_patterns) > 0

    def test_extract_from_json(self, link_extractor, tmp_path, sample_json_data):
        """Test link extraction from JSON file."""
        json_file = tmp_path / "test.json"
        with open(json_file, "w") as f:
            json.dump(sample_json_data, f)

        results = link_extractor.extract_from_json(str(json_file))

        assert results["total_links"] == 3
        assert len(results["unique_links"]) == 3
        assert results["quality_stats"]["flac"] == 1
        assert results["quality_stats"]["mp3_320"] == 1

    def test_extract_from_text(self, link_extractor, tmp_path):
        """Test link extraction from text file."""
        text_content = """
        Download links:
        https://nfile.cc/track1.flac
        https://mediafire.com/track2_320.mp3
        https://mega.nz/track3.zip
        https://nfile.cc/track1.flac  # Duplicate
        """

        text_file = tmp_path / "test.txt"
        with open(text_file, "w") as f:
            f.write(text_content)

        results = link_extractor.extract_from_text(str(text_file))

        assert results["total_links"] == 3  # Should remove duplicate
        assert len(results["unique_links"]) == 3

    def test_analyze_link_quality(self, link_extractor):
        """Test link quality analysis."""
        link1 = "https://example.com/track.flac"
        link2 = "https://example.com/track_320.mp3"
        link3 = "https://example.com/track.mp3"

        assert link_extractor._analyze_link_quality(link1) == "flac"
        assert link_extractor._analyze_link_quality(link2) == "mp3_320"
        assert link_extractor._analyze_link_quality(link3) == "other"


class TestModels:
    """Test cases for Pydantic models."""

    def test_download_link_model(self):
        """Test DownloadLink model validation."""
        # Valid link
        link = DownloadLink(url="https://example.com/track.flac")
        assert link.format == "flac"
        assert link.quality == "lossless"
        assert link.host == "example.com"

        # Invalid URL should raise error
        with pytest.raises(Exception):
            DownloadLink(url="not-a-valid-url")

    def test_blog_post_model(self):
        """Test BlogPost model validation."""
        post_data = {
            "url": "https://example.com/post",
            "title": "Test Post",
            "post_date": "2024-01-15",
            "genres": ["House", "TECHNO"],  # Should be normalized
            "download_links": [{"url": "https://example.com/track.flac"}],
        }

        post = BlogPost(**post_data)

        assert post.title == "Test Post"
        assert post.post_date == date(2024, 1, 15)
        assert post.genres == ["house", "techno"]  # Normalized
        assert len(post.download_links) == 1

    def test_genre_model(self):
        """Test Genre model validation."""
        genre = Genre(name="Progressive House", weight=10, aliases=["Prog House", "Progressive"])

        assert genre.name == "progressive house"  # Normalized
        assert genre.weight == 10
        assert genre.aliases == ["prog house", "progressive"]  # Normalized

        # Test matching
        assert genre.matches("This is a progressive house mix")
        assert genre.matches("Love this prog house track")

    def test_scraper_config_validation(self):
        """Test ScraperConfig model validation."""
        # Valid config
        config = ScraperConfig(
            base_url="https://example.com",
            output_file="results.txt",
            max_pages=20,
            target_genres=["House", "Techno"],
        )

        assert config.output_file == "results.txt"
        assert config.target_genres == ["house", "techno"]  # Normalized

        # Test date validation
        with pytest.raises(ValueError):
            ScraperConfig(
                base_url="https://example.com",
                start_date=date(2024, 12, 31),
                end_date=date(2024, 1, 1),  # End before start
            )


class TestErrorHandling:
    """Test cases for error handling utilities."""

    def test_validate_url(self):
        """Test URL validation."""
        assert validate_url("https://example.com") is True
        assert validate_url("http://example.com/path") is True
        assert validate_url("not-a-url") is False
        assert validate_url("") is False
        assert validate_url(None) is False

    @patch("time.sleep")
    def test_exponential_backoff_decorator(self, mock_sleep):
        """Test exponential backoff decorator."""
        call_count = 0

        @exponential_backoff
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Network error")
            return "Success"

        result = flaky_function()

        assert result == "Success"
        assert call_count == 3
        assert mock_sleep.call_count == 2  # Should sleep twice

    def test_rate_limit_handler(self):
        """Test rate limit response handling."""
        # Test with Retry-After header
        response = Mock()
        response.status_code = 429
        response.headers = {"Retry-After": "30"}

        delay = rate_limit_handler(response)
        assert delay == 30

        # Test without Retry-After header
        response.headers = {}
        delay = rate_limit_handler(response)
        assert delay == 60  # Default delay

        # Test non-rate-limited response
        response.status_code = 200
        delay = rate_limit_handler(response)
        assert delay is None


class TestIntegration:
    """Integration tests for the complete scraping flow."""

    @patch("music_scraper.MusicBlogScraper.get_page_content")
    @patch("music_scraper.MusicBlogScraper.find_blog_posts")
    def test_complete_scraping_flow(
        self, mock_find_posts, mock_get_page, scraper, sample_html, tmp_path
    ):
        """Test complete scraping workflow."""
        # Setup mocks
        mock_find_posts.return_value = ["https://example.com/post1", "https://example.com/post2"]
        mock_get_page.return_value = BeautifulSoup(sample_html, "html.parser")

        # Set output to temp directory
        scraper.output_file = str(tmp_path / "results.txt")

        # Run scraping workflow
        post_urls = scraper.find_blog_posts(max_pages=1)
        matching_posts = scraper.filter_posts_by_genre(post_urls, ["progressive house", "melodic"])
        scraper.save_results(matching_posts)

        # Verify results
        assert len(post_urls) == 2
        assert len(matching_posts) == 2
        assert os.path.exists(scraper.output_file)

        # Verify file content
        with open(scraper.output_file, "r") as f:
            content = f.read()
            assert "Progressive House Mix 2024" in content
            assert "https://nfile.cc/track123.flac" in content


@pytest.mark.asyncio
class TestAsyncScraper:
    """Test cases for async scraper functionality."""

    async def test_async_scraper_initialization(self):
        """Test async scraper initialization."""
        scraper = AsyncMusicBlogScraper(
            "https://example.com", "async_output.txt", max_concurrent=10
        )

        assert scraper.base_url == "https://example.com"
        assert scraper.max_concurrent == 10
        assert scraper.semaphore._value == 10

    @patch("aiohttp.ClientSession.get")
    async def test_fetch_page_async(self, mock_get):
        """Test async page fetching."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.text = MagicMock(return_value="<html>Test</html>")
        mock_response.__aenter__ = MagicMock(return_value=mock_response)
        mock_response.__aexit__ = MagicMock(return_value=None)

        mock_get.return_value = mock_response

        scraper = AsyncMusicBlogScraper("https://example.com")

        # Create session context
        async with scraper.create_session() as session:
            result = await scraper.fetch_page(session, "https://example.com/test")

            assert result == "<html>Test</html>"
            mock_get.assert_called_once()


# Parametrized tests
@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://example.com/2024/01/15/post/", True),
        ("/djs-chart/house-mix/", True),
        ("/category/music/", False),
        ("/wp-admin/", False),
        ("/style.css", False),
    ],
)
def test_is_blog_post_url_parametrized(scraper, url, expected):
    """Parametrized test for blog post URL detection."""
    assert scraper.is_blog_post_url(url) == expected


@pytest.mark.parametrize(
    "date_str,expected",
    [
        ("2024-01-15", date(2024, 1, 15)),
        ("01/15/2024", date(2024, 1, 15)),
        ("January 15, 2024", date(2024, 1, 15)),
        ("15 Jan 2024", date(2024, 1, 15)),
        ("invalid", None),
        ("", None),
    ],
)
def test_parse_date_string_parametrized(scraper, date_str, expected):
    """Parametrized test for date string parsing."""
    assert scraper.parse_date_string(date_str) == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
