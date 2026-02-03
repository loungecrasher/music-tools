#!/usr/bin/env python3
"""
EDM Music Blog Scraper
Automatically finds blog posts by genre keywords and extracts download links.
"""

import argparse
import logging
import re
from datetime import date, datetime
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# Import configuration
from .config import (
    ALL_EDM_GENRES,
    BLOG_POST_SELECTORS,
    DATE_FORMATS,
    DATE_PATTERNS,
    DATE_SELECTORS,
    DEFAULT_ENCODING,
    DEFAULT_GENRES,
    DEFAULT_MAX_PAGES,
    DEFAULT_OUTPUT_FILE,
    DOWNLOAD_PATTERNS,
    GENRE_SELECTORS,
    GROUP_SIZE,
    MAX_EMPTY_PAGES,
    MAX_GENRE_LENGTH,
    MAX_PAGES_LIMIT,
    MAX_TITLE_LENGTH,
    MAX_URL_LENGTH,
    META_DATE_SELECTORS,
    PAGINATION_PATTERNS,
    POST_URL_INDICATORS,
    POSTS_PER_PAGE_ESTIMATE,
    RELEASE_IDENTIFIER_PATTERNS,
    REQUEST_DELAY,
    REQUEST_TIMEOUT,
    SKIP_URL_PATTERNS,
    TITLE_SELECTORS,
    URL_DATE_PATTERNS,
    USER_AGENTS,
    VALID_HOSTS,
)

# Import error handling utilities
from .error_handling import (
    RateLimitError,
    ScrapingError,
    ThreadSafeRateLimiter,
    ValidationError,
    create_resilient_session,
    exponential_backoff,
    log_progress,
    parse_content_safely,
    rate_limiter,
    safe_file_read,
    safe_request,
    sanitize_filename,
    validate_file_path,
    validate_host,
    validate_url,
)

# Import link extractor for automatic link extraction
from .link_extractor import LinkExtractor
from .models import BlogPost, DownloadLink, ScraperConfig, ScraperResult, validate_post_data

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MusicBlogScraper:
    def __init__(self, base_url: str, output_file: str = DEFAULT_OUTPUT_FILE):
        """
        Initialize the scraper.

        Args:
            base_url: The base URL of the blog site
            output_file: Name of the output file for download links
        """
        if not validate_url(base_url):
            raise ValidationError(f"Invalid base URL: {base_url}")

        self.base_url = base_url.rstrip('/')
        self.output_file = sanitize_filename(output_file)
        self.session = create_resilient_session()
        self.rate_limiter = ThreadSafeRateLimiter()

        # Use pre-compiled patterns from config
        self.download_patterns = DOWNLOAD_PATTERNS
        self.release_identifier_patterns = RELEASE_IDENTIFIER_PATTERNS

    def get_page_content(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a web page with enhanced error handling and retries."""
        if not validate_url(url):
            logger.error(f"Invalid URL: {url}")
            return None

        # Apply rate limiting
        domain = urlparse(url).netloc
        self.rate_limiter.wait_if_needed(domain)

        # Use the safe_request function with proper error handling
        response = safe_request(self.session, url)
        if not response:
            return None

        # Parse content safely
        soup = parse_content_safely(response)
        if not soup:
            logger.warning(f"Could not parse content from {url}")
            return None

        return soup

    def scrape_website(self, max_pages: int = DEFAULT_MAX_PAGES, start_date=None, end_date=None) -> List[Dict]:
        """
        Main entry point to scrape the website.

        Args:
            max_pages: Maximum number of pages to scan
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of dictionaries containing post details
        """
        logger.info(f"Starting scrape of {self.base_url}")

        # 1. Find post URLs
        post_urls = self.find_blog_posts(max_pages, start_date, end_date)

        if not post_urls:
            logger.warning("No posts found to process")
            return []

        # 2. Filter/Process posts
        # Use preferred_genres if available (from subclass), otherwise use all genres
        target_genres = getattr(self, 'preferred_genres', ALL_EDM_GENRES)

        results = self.filter_posts_by_genre(post_urls, target_genres, start_date, end_date)
        return results

    def find_blog_posts(self, max_pages: int = DEFAULT_MAX_PAGES, start_date=None, end_date=None) -> List[str]:
        """
        Find blog post URLs with date-aware scanning to stop when posts get too old.

        Args:
            max_pages: Maximum number of pages to search through
            start_date: Start date for filtering (stops scanning when posts get older)
            end_date: End date for filtering

        Returns:
            List of blog post URLs within date range
        """
        # Validate max_pages
        max_pages = min(max_pages, MAX_PAGES_LIMIT)

        post_urls = []
        page_num = 1

        # First, try to get posts from the main page
        logger.info(f"Scanning main page: {self.base_url}")
        main_soup = self.get_page_content(self.base_url)
        if main_soup:
            main_posts = self.extract_posts_from_page(main_soup, self.base_url)
            post_urls.extend(main_posts)
            logger.info(f"Found {len(main_posts)} posts on main page")
        else:
            logger.error("Could not access main page")
            return []

        # Calculate intelligent pagination depth based on date range
        if start_date:
            # Estimate pages needed: assume ~12-15 posts per page, ~1-2 posts per day
            from datetime import datetime
            days_to_scan = (datetime.now().date() - start_date).days
            estimated_pages = max(DEFAULT_MAX_PAGES, min(MAX_PAGES_LIMIT, days_to_scan // 2))  # 2 days per page average
            intelligent_max_pages = min(max_pages, estimated_pages)

            if intelligent_max_pages < max_pages:
                logger.info(f"📅 Date range: {days_to_scan} days")
                logger.info(f"🎯 Intelligent pagination: Using {intelligent_max_pages} pages instead of {max_pages}")
                logger.info(f"   (Estimated {days_to_scan // 2} days per page, {days_to_scan} total days)")
            else:
                logger.info(f"📅 Date range: {days_to_scan} days")
                logger.info(f"🎯 Using requested {max_pages} pages (within reasonable range)")
        else:
            intelligent_max_pages = min(max_pages, MAX_PAGES_LIMIT)  # Default limit
            logger.info(f"🎯 Using {intelligent_max_pages} pages (no date range specified)")

        # Start from page 2 since page 1 is the same as main page
        page_num = 2
        pages_without_target_content = 0

        # Create progress bar for pagination
        with tqdm(total=intelligent_max_pages, initial=1, desc="Scanning pages", unit="page") as pbar:
            while page_num <= intelligent_max_pages + 1:
                logger.info(f"Scanning page {page_num}/{intelligent_max_pages + 1}...")

                # Try ONLY the correct sharing-db.club format
                pagination_urls = [
                    f"{self.base_url}/page/{page_num}/",          # sharing-db.club format with trailing slash - FIRST!
                    f"{self.base_url}/page/{page_num}",           # sharing-db.club format without trailing slash - SECOND!
                ]

                page_found = False
                page_posts = []

                for page_url in pagination_urls:
                    soup = self.get_page_content(page_url)
                    if soup:
                        page_posts = self.extract_posts_from_page(soup, page_url)

                        # Only add new posts (avoid duplicates)
                        new_posts = [url for url in page_posts if url not in post_urls]
                        if new_posts:
                            page_found = True
                            logger.info(f"Found {len(new_posts)} new posts using: {page_url}")
                            break

                if not page_found:
                    pages_without_target_content += 1
                    if pages_without_target_content >= MAX_EMPTY_PAGES:
                        logger.info(f"No new posts found on {MAX_EMPTY_PAGES} consecutive pages, stopping search")
                        break
                    logger.info(f"No new posts found on page {page_num}, continuing...")
                else:
                    pages_without_target_content = 0  # Reset counter

                # Add posts from this page - let final filtering handle date ranges
                # Remove the overly aggressive date-aware scanning that was stopping prematurely

                # Add posts from this page
                new_posts = [url for url in page_posts if url not in post_urls]
                post_urls.extend(new_posts)
                logger.info(f"Added {len(new_posts)} posts (total: {len(post_urls)})")

                page_num += 1
                pbar.update(1)

        # Remove duplicates while preserving order
        unique_posts = []
        seen = set()
        for url in post_urls:
            if url not in seen:
                unique_posts.append(url)
                seen.add(url)

        logger.info(f"Total unique posts discovered: {len(unique_posts)}")
        return unique_posts

    def extract_posts_from_page(self, soup, page_url: str) -> List[str]:
        """Extract blog post URLs from a single page with multiple strategies."""
        found_posts = []

        # Use selectors from configuration
        for selector in BLOG_POST_SELECTORS:
            try:
                links = soup.select(selector)
                for link in links:
                    href = link.get('href')
                    if href and self.is_blog_post_url(href):
                        full_url = urljoin(page_url, href)
                        if full_url not in found_posts:
                            found_posts.append(full_url)
            except Exception as e:
                logger.debug(f"Error with selector '{selector}': {e}")
                continue

        return found_posts

    def is_blog_post_url(self, url: str) -> bool:
        """Check if URL looks like a blog post with enhanced patterns for sharing-db.club."""
        if not url or not isinstance(url, str):
            return False

        # Skip common non-post URLs using configuration patterns
        for pattern in SKIP_URL_PATTERNS:
            if pattern in url.lower():
                return False

        # Check for post indicators using configuration patterns
        for indicator in POST_URL_INDICATORS:
            if indicator in url.lower():
                return True

        # Also check if it's a direct content URL with the base domain
        # and doesn't look like a static resource
        if self.base_url in url and not any(skip in url.lower() for skip in ['.css', '.js', '.png', '.jpg', '.gif']):
            # If it has numbers (likely dates or IDs), consider it a post
            if re.search(r'\d{4}', url):  # Contains a 4-digit number (likely year)
                return True

        return False

    def extract_genre_keywords(self, soup: BeautifulSoup) -> List[str]:
        """
        Extract genre keywords from a blog post with aggressive detection for sharing-db.club.

        Args:
            soup: BeautifulSoup object of the blog post

        Returns:
            List of genre keywords found
        """
        genres = []

        try:
            # Strategy 1: Check the URL path itself for genre indicators
            canonical_link = soup.find('link', {'rel': 'canonical'})
            if canonical_link:
                url = canonical_link.get('href', '')
                if '/house/' in url:
                    genres.append('house')
                elif '/techno/' in url:
                    genres.append('techno')
                elif '/trance/' in url:
                    genres.append('trance')
                elif '/electronic/' in url:
                    genres.append('electronica')

            # Strategy 2: Get ALL text content and search aggressively
            page_content = soup.get_text()

            # Strategy 3: Look for explicit genre labels (sharing-db.club format)
            genre_patterns = [
                r'Genre:\s*([^\n\r]+)',
                r'\*\*Genre:\*\*\s*([^\n\r]+)',  # Fixed: escaped asterisks
                r'Style:\s*([^\n\r]+)',
                r'\*\*Style:\*\*\s*([^\n\r]+)',  # Fixed: escaped asterisks
                r'Genre[s]?:\s*([^\n\r]+)',
                r'posted in\s+([^\n\r]+)',  # WordPress "posted in" categories
            ]

            for pattern in genre_patterns:
                matches = re.findall(pattern, page_content, re.IGNORECASE)
                for match in matches:
                    genres.extend(self.extract_genres_from_text(match))

            # Strategy 4: Check WordPress category links
            category_links = soup.select('a[href*="/category/"]')
            for link in category_links:
                href = link.get('href', '')
                text = link.get_text().strip()
                if text:
                    genres.extend(self.extract_genres_from_text(text))
                # Also extract from URL path
                if '/category/' in href:
                    category = href.split('/category/')[-1].strip('/')
                    genres.extend(self.extract_genres_from_text(category))

            # Strategy 5: Always extract from full content with all preferred genres
            genres.extend(self.extract_genres_from_text(page_content))

            # Strategy 6: If this is sharing-db.club, be more aggressive with common patterns
            if 'sharing-db.club' in str(soup):
                # Look for any mention of our preferred genres in the content
                preferred_genres = [
                    'house', 'progressive house', 'melodic', 'indie dance', 'bass house',
                    'organic house', 'drum and bass', 'uk garage', 'electro pop', 'nu disco',
                    'funky', 'deep house', 'tech house', 'dance', 'afro house', 'brazilian',
                    'latin', 'electronica', 'ambient', 'techno', 'trance', 'minimal'
                ]

                content_lower = page_content.lower()
                for genre in preferred_genres:
                    if genre.lower() in content_lower:
                        genres.append(genre)

        except Exception as e:
            logger.warning(f"Error in genre extraction: {e}")
            # Fallback: just extract from content
            try:
                genres.extend(self.extract_genres_from_text(soup.get_text()))
            except Exception as fallback_error:
                logger.error(f"Fallback genre extraction failed: {fallback_error}")

        # Remove duplicates and return
        unique_genres = list(set(genres))
        return unique_genres

    def extract_genres_from_text(self, text: str) -> List[str]:
        """Extract genre keywords from text."""
        # Handle BeautifulSoup objects
        if hasattr(text, 'get_text'):
            text = text.get_text()

        if not text:
            return []

        # Use genres from configuration
        found_genres = []
        text_lower = text.lower()

        for genre in ALL_EDM_GENRES:
            if genre in text_lower:
                found_genres.append(genre)

        return found_genres

    def extract_download_links(self, soup: BeautifulSoup, post_url: str) -> List[str]:
        """
        Extract download links from a blog post with quality preference.

        Args:
            soup: BeautifulSoup object of the blog post
            post_url: URL of the blog post

        Returns:
            List of download links found (prioritized by quality)
        """
        download_links = []
        flac_links = []
        mp3_320_links = []
        other_links = []

        # Find all links on the page
        links = soup.find_all('a', href=True)

        for link in links:
            href = link.get('href')
            if href:
                # Skip internal site links (feeds, trackbacks, etc.)
                if any(skip_pattern in href.lower() for skip_pattern in ['/feed/', '/trackback/', self.base_url]):
                    continue

                # Check if it matches download patterns using pre-compiled patterns
                for pattern in self.download_patterns:
                    if pattern.search(href):
                        full_url = urljoin(post_url, href)

                        # Validate the URL
                        if not validate_url(full_url):
                            continue

                        # Skip if it's an internal site URL after URL joining
                        if self.base_url in full_url and not any(host in full_url for host in VALID_HOSTS):
                            continue

                        # Categorize links by quality preference
                        if self.is_flac_link(full_url, link):
                            flac_links.append(full_url)
                        elif self.is_mp3_320_link(full_url, link):
                            mp3_320_links.append(full_url)
                        else:
                            other_links.append(full_url)

        # Also search in the page text for download links
        page_text = soup.get_text()
        for pattern in self.download_patterns:
            try:
                matches = pattern.findall(page_text)
                for match in matches:
                    if isinstance(match, str) and match not in download_links:
                        # Validate the URL
                        if not validate_url(match):
                            continue

                        # Categorize text-based links
                        if self.is_flac_link_from_text(match, page_text):
                            flac_links.append(match)
                        elif self.is_mp3_320_link_from_text(match, page_text):
                            mp3_320_links.append(match)
                        else:
                            other_links.append(match)
            except Exception as e:
                logger.debug(f"Error processing pattern {pattern}: {e}")
                continue

        # Prioritize FLAC over MP3 320kbps, then other links
        # Remove duplicates while maintaining priority order
        seen_links = set()

        # Add FLAC links first (highest priority)
        for link in flac_links:
            if link not in seen_links:
                download_links.append(link)
                seen_links.add(link)

        # Add MP3 320kbps links only if no FLAC version exists
        for link in mp3_320_links:
            if link not in seen_links:
                # Check if we already have a FLAC version of this release
                if not self.has_flac_version(link, flac_links):
                    download_links.append(link)
                    seen_links.add(link)

        # Add other links
        for link in other_links:
            if link not in seen_links:
                download_links.append(link)
                seen_links.add(link)

        return download_links

    def is_flac_link(self, url: str, link_element) -> bool:
        """Check if a link is for FLAC files."""
        url_lower = url.lower()
        link_text = link_element.get_text().lower()

        # Exclude if it contains 320 indicators
        if '320' in link_text or '320' in url_lower:
            return False

        # Check URL for FLAC indicators
        flac_indicators = ['flac', '.flac', 'lossless']
        if any(indicator in url_lower for indicator in flac_indicators):
            return True

        # Check link text for FLAC indicators - be very specific
        if 'download in flac' in link_text or 'download in fl' in link_text:
            return True
        if link_text.strip() == 'flac' or '(flac)' in link_text or 'flac)' in link_text:
            return True

        # Check for FLAC in surrounding text (like "DOWNLOAD in FLAC")
        parent_text = link_element.parent.get_text().lower() if link_element.parent else ""
        if 'download in flac' in parent_text and '320' not in parent_text:
            return True

        return False

    def is_mp3_320_link(self, url: str, link_element) -> bool:
        """Check if a link is for MP3 320kbps files."""
        url_lower = url.lower()
        link_text = link_element.get_text().lower()

        # Exclude if it contains FLAC indicators
        if 'flac' in link_text or 'flac' in url_lower:
            return False

        # Check URL for MP3 320 indicators
        mp3_320_indicators = ['320', '320kbps', '320 kbps', 'mp3 320']
        if any(indicator in url_lower for indicator in mp3_320_indicators):
            return True

        # Check link text for MP3 320 indicators - be specific to avoid false positives
        if 'download in 320' in link_text or 'download in 320kbps' in link_text:
            return True
        if '(320kbps)' in link_text or '320kbps)' in link_text or '(320)' in link_text:
            return True

        # Check for MP3 320 in surrounding text
        parent_text = link_element.parent.get_text().lower() if link_element.parent else ""
        if 'download in 320' in parent_text and 'flac' not in parent_text:
            return True

        return False

    def is_flac_link_from_text(self, url: str, page_text: str) -> bool:
        """Check if a text-based link is for FLAC files."""
        url_lower = url.lower()
        page_text_lower = page_text.lower()

        # Check URL for FLAC indicators
        flac_indicators = ['flac', '.flac', 'lossless']
        if any(indicator in url_lower for indicator in flac_indicators):
            return True

        # Look for FLAC indicators near the URL in the page text
        # Find the URL position and check surrounding text
        url_pos = page_text_lower.find(url_lower)
        if url_pos != -1:
            # Check text around the URL (±100 characters)
            start = max(0, url_pos - 100)
            end = min(len(page_text_lower), url_pos + len(url_lower) + 100)
            surrounding_text = page_text_lower[start:end]

            if any(indicator in surrounding_text for indicator in flac_indicators):
                return True

        return False

    def is_mp3_320_link_from_text(self, url: str, page_text: str) -> bool:
        """Check if a text-based link is for MP3 320kbps files."""
        url_lower = url.lower()
        page_text_lower = page_text.lower()

        # Check URL for MP3 320 indicators
        mp3_320_indicators = ['320', '320kbps', '320 kbps', 'mp3 320']
        if any(indicator in url_lower for indicator in mp3_320_indicators):
            return True

        # Look for MP3 320 indicators near the URL in the page text
        url_pos = page_text_lower.find(url_lower)
        if url_pos != -1:
            # Check text around the URL (±100 characters)
            start = max(0, url_pos - 100)
            end = min(len(page_text_lower), url_pos + len(url_lower) + 100)
            surrounding_text = page_text_lower[start:end]

            if any(indicator in surrounding_text for indicator in mp3_320_indicators):
                return True

        return False

    def has_flac_version(self, mp3_link: str, flac_links: List[str]) -> bool:
        """Check if there's already a FLAC version of this release."""
        # Extract release identifier from MP3 link
        mp3_identifier = self.extract_release_identifier(mp3_link)

        # Check if any FLAC link has the same release identifier
        for flac_link in flac_links:
            flac_identifier = self.extract_release_identifier(flac_link)
            if mp3_identifier and flac_identifier and mp3_identifier == flac_identifier:
                return True

        return False

    def extract_release_identifier(self, url: str) -> str:
        """Extract a release identifier from URL to match different quality versions."""
        # Use pre-compiled patterns from configuration
        for pattern in self.release_identifier_patterns:
            match = pattern.search(url)
            if match:
                return match.group(1)

        return ""

    def filter_posts_by_genre(self, post_urls: List[str], target_genres: List[str],
                              start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[Dict]:
        """
        Filter blog posts by genre keywords and date range.

        Args:
            post_urls: List of blog post URLs
            target_genres: List of genre keywords to search for
            start_date: Start date for filtering (inclusive)
            end_date: End date for filtering (inclusive)

        Returns:
            List of dictionaries with post info and download links
        """
        matching_posts = []

        logger.info(f"Filtering {len(post_urls)} posts for genres: {', '.join(target_genres)}")
        if start_date or end_date:
            date_range = f" from {start_date} to {end_date}" if start_date and end_date else \
                        f" from {start_date}" if start_date else f" until {end_date}"
            logger.info(f"Date range: {date_range}")

        # Create progress bar for processing posts
        with tqdm(total=len(post_urls), desc="Filtering posts by genre", unit="post") as pbar:
            for i, post_url in enumerate(post_urls, 1):
                logger.debug(f"Processing: {post_url}")

                soup = self.get_page_content(post_url)
                if not soup:
                    pbar.update(1)
                    continue

                # Extract post date
                post_date = self.extract_post_date(soup, post_url)

                # Check date range if specified
                if start_date or end_date:
                    if not post_date:
                        logger.debug(f"Could not determine post date for {post_url}, skipping date filter")
                    elif start_date and post_date < start_date:
                        logger.debug(f"Post date {post_date} before start date {start_date}")
                        pbar.update(1)
                        continue
                    elif end_date and post_date > end_date:
                        logger.debug(f"Post date {post_date} after end date {end_date}")
                        pbar.update(1)
                        continue
                    else:
                        logger.debug(f"Post date {post_date} within range")

                # Extract genre keywords
                post_genres = self.extract_genre_keywords(soup)

                # Check if any target genres match
                matching_genres = [genre for genre in target_genres if genre.lower() in [g.lower() for g in post_genres]]

                if matching_genres:
                    # Extract download links
                    download_links = self.extract_download_links(soup, post_url)

                    # Get post title
                    title = self.extract_post_title(soup)

                    # Create validated BlogPost model
                    post_data = {
                        'url': post_url,
                        'title': title,
                        'genres': post_genres,
                        'matching_genres': matching_genres,
                        'download_links': download_links,  # Pass as strings, let Pydantic handle conversion
                        'post_date': post_date
                    }

                    validated_post = validate_post_data(post_data)
                    if validated_post:
                        # Convert to dict and ensure download_links are strings for compatibility
                        post_dict = validated_post.to_dict()
                        # Convert DownloadLink objects (which contain HttpUrl objects) back to strings
                        if 'download_links' in post_dict:
                            converted_links = []
                            for link in post_dict['download_links']:
                                if isinstance(link, dict) and 'url' in link:
                                    # DownloadLink object converted to dict
                                    converted_links.append(str(link['url']))
                                elif hasattr(link, 'url'):
                                    # Direct DownloadLink object
                                    converted_links.append(str(link.url))
                                else:
                                    # String or other format
                                    converted_links.append(str(link))
                            post_dict['download_links'] = converted_links
                        matching_posts.append(post_dict)
                        logger.debug(f"Found {len(download_links)} download links")
                    else:
                        logger.warning(f"Failed to validate post data for {post_url}")
                else:
                    logger.debug("No matching genres found")

                pbar.update(1)

        return matching_posts

    def extract_post_title(self, soup: BeautifulSoup) -> str:
        """Extract the title of a blog post."""
        # Use selectors from configuration
        for selector in TITLE_SELECTORS:
            element = soup.select_one(selector)
            if element:
                title = element.get_text().strip()
                if title and len(title) <= MAX_TITLE_LENGTH:
                    return title

        return "Unknown Title"

    def extract_post_date(self, soup: BeautifulSoup, post_url: str) -> Optional[date]:
        """Extract the publication date of a blog post."""
        # Try to find date in HTML elements using configuration selectors
        for selector in DATE_SELECTORS:
            element = soup.select_one(selector)
            if element:
                date_text = element.get_text().strip()
                parsed_date = self.parse_date_string(date_text)
                if parsed_date:
                    return parsed_date

        # Try to find date in meta tags using configuration selectors
        for selector in META_DATE_SELECTORS:
            element = soup.select_one(selector)
            if element:
                date_text = element.get('content', '').strip()
                parsed_date = self.parse_date_string(date_text)
                if parsed_date:
                    return parsed_date

        # Try to extract date from URL using configuration patterns
        url_date = self.extract_date_from_url(post_url)
        if url_date:
            return url_date

        # Try to find date in page text using configuration patterns
        page_text = soup.get_text()
        for pattern in DATE_PATTERNS:
            match = pattern.search(page_text)
            if match:
                parsed_date = self.parse_date_string(match.group(1))
                if parsed_date:
                    return parsed_date

        return None

    def parse_date_string(self, date_text: str) -> Optional[date]:
        """Parse various date string formats into a date object."""
        if not date_text:
            return None

        # Clean up text (handle newlines in "Nov\n21\n2025" format)
        date_text = re.sub(r'\s+', ' ', date_text.strip())

        # Use date formats from configuration
        for fmt in DATE_FORMATS:
            try:
                parsed_date = datetime.strptime(date_text, fmt).date()
                # Validate the parsed date
                if self.is_valid_date(parsed_date):
                    return parsed_date
            except ValueError:
                continue

        return None

    def is_valid_date(self, date_obj: date) -> bool:
        """Validate if a date object is reasonable."""
        if not date_obj:
            return False

        # Check if date is in reasonable range (not too far in past or future)
        current_year = datetime.now().year
        if date_obj.year < 1990 or date_obj.year > current_year + 1:
            return False

        # Check if month and day are valid
        try:
            # This will raise ValueError if month/day are invalid
            date_obj.replace(year=date_obj.year, month=date_obj.month, day=date_obj.day)
            return True
        except ValueError:
            return False

    def extract_date_from_url(self, url: str) -> Optional[date]:
        """Extract date from URL patterns like /2024/01/15/ or /2024-01-15/."""
        # Use URL date patterns from configuration
        for pattern in URL_DATE_PATTERNS:
            match = pattern.search(url)
            if match:
                try:
                    if len(match.groups()) == 3:
                        year, month, day = match.groups()
                    else:
                        # For patterns like 20240115
                        date_str = match.group(1)
                        year, month, day = date_str[:4], date_str[4:6], date_str[6:8]

                    parsed_date = date(int(year), int(month), int(day))
                    # Validate the parsed date
                    if self.is_valid_date(parsed_date):
                        return parsed_date
                except (ValueError, IndexError):
                    continue

        return None

    def save_results(self, matching_posts: List[Dict]):
        """Save results to text file with automatic link extraction."""
        try:
            # First, save the detailed results
            with open(self.output_file, 'w', encoding=DEFAULT_ENCODING) as f:
                f.write(f"EDM Music Download Links - Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 80 + "\n\n")

                for post in matching_posts:
                    f.write(f"Title: {post['title']}\n")
                    f.write(f"URL: {post['url']}\n")
                    if post.get('post_date'):
                        f.write(f"Date: {post['post_date']}\n")
                    f.write(f"Genres: {', '.join(post['genres'])}\n")
                    f.write(f"Matching Genres: {', '.join(post['matching_genres'])}\n")
                    f.write("Download Links:\n")

                    if post['download_links']:
                        for link in post['download_links']:
                            f.write(f"  - {link}\n")
                    else:
                        f.write("  No download links found\n")

                    f.write("\n" + "-" * 60 + "\n\n")

            logger.info(f"Results saved to {self.output_file}")
            logger.info(f"Found {len(matching_posts)} matching posts")

            total_links = sum(len(post['download_links']) for post in matching_posts)
            logger.info(f"Total download links found: {total_links}")

            # Now automatically extract and append all unique links
            if total_links > 0:
                logger.info("Automatically extracting all unique download links...")

                # Collect all unique links
                all_links = set()
                quality_stats = {'flac': 0, 'mp3_320': 0, 'other': 0}

                for post in matching_posts:
                    for link in post.get('download_links', []):
                        # Handle different link formats
                        if isinstance(link, dict):
                            # If link is a dictionary, extract the URL
                            link_url = link.get('url', '')
                        elif hasattr(link, 'strip'):
                            # If link is a string-like object
                            link_url = str(link) if link else ''
                        else:
                            # If link is an HttpUrl or other object, convert to string
                            link_url = str(link) if link else ''

                        if link_url and link_url.strip():
                            link_url = link_url.strip()
                            all_links.add(link_url)

                            # Track quality stats
                            link_lower = link_url.lower()
                            if 'flac' in link_lower or '.flac' in link_lower:
                                quality_stats['flac'] += 1
                            elif '320' in link_lower:
                                quality_stats['mp3_320'] += 1
                            else:
                                quality_stats['other'] += 1

                # Sort links for consistent output
                unique_links = sorted(list(all_links))

                # Append extracted links section to the same file
                with open(self.output_file, 'a', encoding=DEFAULT_ENCODING) as f:
                    f.write("\n\n" + "=" * 80 + "\n")
                    f.write("ALL UNIQUE DOWNLOAD LINKS (EXTRACTED)\n")
                    f.write("=" * 80 + "\n\n")

                    # Write summary statistics
                    f.write("EXTRACTION STATISTICS\n")
                    f.write("-" * 20 + "\n")
                    f.write(f"Total posts processed: {len(matching_posts)}\n")
                    f.write(f"Total unique links: {len(unique_links)}\n")
                    f.write("\nQuality breakdown:\n")
                    f.write(f"  FLAC/Lossless: {quality_stats['flac']}\n")
                    f.write(f"  MP3 320kbps: {quality_stats['mp3_320']}\n")
                    f.write(f"  Other: {quality_stats['other']}\n")
                    f.write("\n" + "=" * 80 + "\n\n")

                    # Write links in groups
                    for i, link in enumerate(unique_links):
                        # Add group header at the start of each group
                        if i % GROUP_SIZE == 0:
                            group_num = (i // GROUP_SIZE) + 1
                            total_groups = (len(unique_links) + GROUP_SIZE - 1) // GROUP_SIZE
                            f.write(f"=== GROUP {group_num} of {total_groups} ===\n")

                        f.write(f"{link}\n")

                        # Add a blank line after every group (except the last)
                        if (i + 1) % GROUP_SIZE == 0 and (i + 1) < len(unique_links):
                            f.write("\n")

                logger.info(f"✅ Extracted {len(unique_links)} unique download links")
                logger.info(f"   FLAC/Lossless: {quality_stats['flac']}")
                logger.info(f"   MP3 320kbps: {quality_stats['mp3_320']}")
                logger.info(f"   Other: {quality_stats['other']}")

        except IOError as e:
            logger.error(f"Error saving results to {self.output_file}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error saving results: {e}")
            raise


def main():
    parser = argparse.ArgumentParser(description='Scrape EDM blog for music downloads by genre')
    parser.add_argument('url', help='Base URL of the blog site')
    parser.add_argument('--genres', nargs='+',
                        default=DEFAULT_GENRES,
                        help='Genre keywords to search for (default: house progressive house melodic indie dance bass house)')
    parser.add_argument('--output', default=DEFAULT_OUTPUT_FILE,
                        help='Output file name (default: download_links.txt)')
    parser.add_argument('--max-pages', type=int, default=DEFAULT_MAX_PAGES,
                        help='Maximum pages to search (default: 10)')
    parser.add_argument('--start-date',
                        help='Start date for filtering (YYYY-MM-DD format, inclusive)')
    parser.add_argument('--end-date',
                        help='End date for filtering (YYYY-MM-DD format, inclusive)')

    args = parser.parse_args()

    # Validate URL
    if not validate_url(args.url):
        print(f"Error: Invalid URL format: {args.url}")
        return 1

    # Validate output file path
    if not validate_file_path(args.output):
        print(f"Error: Invalid output file path: {args.output}")
        return 1

    # Parse date arguments
    start_date = None
    end_date = None

    if args.start_date:
        try:
            start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
        except ValueError:
            print("Error: Invalid start date format. Use YYYY-MM-DD (e.g., 2024-01-15)")
            return 1

    if args.end_date:
        try:
            end_date = datetime.strptime(args.end_date, '%Y-%m-%d').date()
        except ValueError:
            print("Error: Invalid end date format. Use YYYY-MM-DD (e.g., 2024-12-31)")
            return 1

    if start_date and end_date and start_date > end_date:
        print("Error: Start date cannot be after end date")
        return 1

    # Validate max_pages
    if args.max_pages <= 0 or args.max_pages > MAX_PAGES_LIMIT:
        print(f"Error: max-pages must be between 1 and {MAX_PAGES_LIMIT}")
        return 1

    try:
        # Create scraper instance
        scraper = MusicBlogScraper(args.url, args.output)

        # Find all blog posts with date-aware scanning
        print(f"Searching for blog posts on {args.url}")
        post_urls = scraper.find_blog_posts(args.max_pages, start_date, end_date)

        if not post_urls:
            print("No blog posts found. Please check the URL and try again.")
            return 1

        # Filter posts by genre and date range
        matching_posts = scraper.filter_posts_by_genre(post_urls, args.genres, start_date, end_date)

        # Save results
        scraper.save_results(matching_posts)

        print("✅ Scraping completed successfully!")
        print(f"   Found {len(matching_posts)} matching posts")
        total_links = sum(len(post['download_links']) for post in matching_posts)
        print(f"   Total download links: {total_links}")
        print(f"   Results saved to: {args.output}")

        return 0

    except KeyboardInterrupt:
        print("\nScraping interrupted by user.")
        return 1
    except ValidationError as e:
        print(f"Validation error: {e}")
        return 1
    except ScrapingError as e:
        print(f"Scraping error: {e}")
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    main()
