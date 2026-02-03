#!/usr/bin/env python3
"""
Async/Concurrent EDM Music Blog Scraper
Implements asynchronous scraping for improved performance.
"""

import argparse
import asyncio
import logging
import random
import re
import time
from contextlib import asynccontextmanager
from datetime import date, datetime
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse

import aiohttp
from aiohttp import ClientSession, ClientTimeout, TCPConnector
from bs4 import BeautifulSoup

# Import configuration
from .config import (
    ALL_EDM_GENRES,
    BLOG_POST_SELECTORS,
    DATE_FORMATS,
    DATE_PATTERNS,
    DATE_SELECTORS,
    DEFAULT_ENCODING,
    DEFAULT_MAX_PAGES,
    DEFAULT_OUTPUT_FILE,
    DOWNLOAD_PATTERNS,
    GENRE_SELECTORS,
    MAX_CONCURRENT_REQUESTS,
    MAX_CONCURRENT_REQUESTS_PER_HOST,
    MAX_PAGES_LIMIT,
    META_DATE_SELECTORS,
    PAGINATION_PATTERNS,
    POST_URL_INDICATORS,
    RATE_LIMIT_MAX_DELAY,
    RATE_LIMIT_MIN_DELAY,
    RELEASE_IDENTIFIER_PATTERNS,
    REQUEST_TIMEOUT,
    SKIP_URL_PATTERNS,
    TITLE_SELECTORS,
    URL_DATE_PATTERNS,
    USER_AGENTS,
    VALID_HOSTS,
)

# Import error handling utilities
from .error_handling import (
    AsyncRateLimiter,
    ContentError,
    NetworkError,
    RateLimitError,
    ScrapingError,
    ValidationError,
    get_random_user_agent,
    validate_url,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AsyncMusicBlogScraper:
    """Asynchronous music blog scraper for improved performance."""

    def __init__(self, base_url: str, output_file: str = "async_download_links.txt",
                 max_concurrent: int = MAX_CONCURRENT_REQUESTS):
        """
        Initialize the async scraper.

        Args:
            base_url: The base URL of the blog site
            output_file: Name of the output file for download links
            max_concurrent: Maximum concurrent requests
        """
        if not validate_url(base_url):
            raise ValidationError(f"Invalid base URL: {base_url}")

        self.base_url = base_url.rstrip('/')
        self.output_file = output_file
        self.max_concurrent = min(max_concurrent, MAX_CONCURRENT_REQUESTS)
        self.semaphore = asyncio.Semaphore(self.max_concurrent)

        # Use async rate limiter
        self.rate_limiter = AsyncRateLimiter(RATE_LIMIT_MIN_DELAY, RATE_LIMIT_MAX_DELAY)

        # Use pre-compiled patterns from config
        self.download_patterns = DOWNLOAD_PATTERNS

    @asynccontextmanager
    async def create_session(self):
        """Create an aiohttp session with proper configuration."""
        timeout = ClientTimeout(total=REQUEST_TIMEOUT, connect=10, sock_read=10)
        connector = TCPConnector(
            limit=MAX_CONCURRENT_REQUESTS_PER_HOST,
            limit_per_host=MAX_CONCURRENT_REQUESTS_PER_HOST,
            ttl_dns_cache=300
        )

        headers = {
            'User-Agent': get_random_user_agent(),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

        async with ClientSession(
            timeout=timeout,
            connector=connector,
            headers=headers
        ) as session:
            yield session

    async def rate_limit(self, url: str):
        """Implement rate limiting per domain."""
        domain = urlparse(url).netloc
        current_time = time.time()

        if domain in self.rate_limiter.last_request_time:
            elapsed = current_time - self.rate_limiter.last_request_time[domain]
            delay = random.uniform(RATE_LIMIT_MIN_DELAY, RATE_LIMIT_MAX_DELAY)

            if elapsed < delay:
                await asyncio.sleep(delay - elapsed)

        self.rate_limiter.last_request_time[domain] = time.time()

    async def fetch_page(self, session: ClientSession, url: str) -> Optional[str]:
        """Fetch a single page asynchronously."""
        async with self.semaphore:
            try:
                await self.rate_limit(url)

                async with session.get(url) as response:
                    # Handle rate limiting
                    if response.status == 429:
                        retry_after = response.headers.get('Retry-After', 60)
                        logger.warning(f"Rate limited on {url}. Waiting {retry_after} seconds...")
                        await asyncio.sleep(int(retry_after))
                        # Retry once after rate limit
                        async with session.get(url) as retry_response:
                            retry_response.raise_for_status()
                            return await retry_response.text()

                    response.raise_for_status()
                    return await response.text()

            except aiohttp.ClientError as e:
                logger.error(f"Client error fetching {url}: {e}")
                return None
            except asyncio.TimeoutError:
                logger.error(f"Timeout fetching {url}")
                return None
            except Exception as e:
                logger.error(f"Unexpected error fetching {url}: {e}")
                return None

    async def get_page_content(self, session: ClientSession, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a web page asynchronously."""
        html = await self.fetch_page(session, url)
        if html:
            try:
                return BeautifulSoup(html, 'html.parser')
            except Exception as e:
                logger.error(f"Error parsing HTML from {url}: {e}")
                return None
        return None

    async def find_blog_posts_async(self, session: ClientSession, max_pages: int = DEFAULT_MAX_PAGES) -> List[str]:
        """Find blog post URLs asynchronously."""
        post_urls = []

        # Fetch main page
        logger.info(f"Scanning main page: {self.base_url}")
        main_soup = await self.get_page_content(session, self.base_url)
        if main_soup:
            main_posts = self.extract_posts_from_page(main_soup, self.base_url)
            post_urls.extend(main_posts)
            logger.info(f"Found {len(main_posts)} posts on main page")
        else:
            logger.error("Could not access main page")
            return []

        # Create tasks for pagination pages
        page_tasks = []
        for page_num in range(2, max_pages + 2):
            page_urls = [
                f"{self.base_url}/page/{page_num}/",
                f"{self.base_url}/page/{page_num}"
            ]
            for page_url in page_urls:
                page_tasks.append(self.fetch_page_posts(session, page_url, page_num))

        # Fetch all pages concurrently
        if page_tasks:
            logger.info(f"Fetching {len(page_tasks)} pages concurrently...")
            page_results = await asyncio.gather(*page_tasks, return_exceptions=True)

            for result in page_results:
                if isinstance(result, list):
                    post_urls.extend(result)
                elif isinstance(result, Exception):
                    logger.error(f"Error fetching page: {result}")

        # Remove duplicates
        unique_posts = list(dict.fromkeys(post_urls))
        logger.info(f"Total unique posts discovered: {len(unique_posts)}")
        return unique_posts

    async def fetch_page_posts(self, session: ClientSession, page_url: str, page_num: int) -> List[str]:
        """Fetch posts from a single page."""
        logger.debug(f"Fetching page {page_num}: {page_url}")
        soup = await self.get_page_content(session, page_url)
        if soup:
            posts = self.extract_posts_from_page(soup, page_url)
            if posts:
                logger.info(f"Found {len(posts)} posts on page {page_num}")
                return posts
        return []

    def extract_posts_from_page(self, soup: BeautifulSoup, page_url: str) -> List[str]:
        """Extract blog post URLs from a single page."""
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
        """Check if URL looks like a blog post."""
        # Skip common non-post URLs
        skip_patterns = SKIP_URL_PATTERNS

        for pattern in skip_patterns:
            if pattern in url.lower():
                return False

        # Post indicators
        post_indicators = POST_URL_INDICATORS

        if any(indicator in url.lower() for indicator in post_indicators):
            return True

        # Check for year patterns
        if self.base_url in url and re.search(r'\d{4}', url):
            return True

        return False

    async def process_post(self, session: ClientSession, post_url: str,
                           target_genres: List[str], start_date: Optional[date] = None,
                           end_date: Optional[date] = None) -> Optional[Dict]:
        """Process a single post asynchronously."""
        soup = await self.get_page_content(session, post_url)
        if not soup:
            return None

        # Extract post date
        post_date = self.extract_post_date(soup, post_url)

        # Check date range if specified
        if start_date or end_date:
            if not post_date:
                logger.debug(f"Could not determine post date for {post_url}")
            elif start_date and post_date < start_date:
                logger.debug(f"Post date {post_date} before start date {start_date}")
                return None
            elif end_date and post_date > end_date:
                logger.debug(f"Post date {post_date} after end date {end_date}")
                return None

        # Extract genre keywords
        post_genres = self.extract_genre_keywords(soup)

        # Check if any target genres match
        matching_genres = [genre for genre in target_genres
                           if genre.lower() in [g.lower() for g in post_genres]]

        if matching_genres:
            # Extract download links
            download_links = self.extract_download_links(soup, post_url)

            # Get post title
            title = self.extract_post_title(soup)

            post_info = {
                'url': post_url,
                'title': title,
                'genres': post_genres,
                'matching_genres': matching_genres,
                'download_links': download_links,
                'post_date': post_date.isoformat() if post_date else None
            }

            logger.debug(f"Found {len(download_links)} download links for: {title}")
            return post_info

        return None

    async def filter_posts_by_genre_async(self, session: ClientSession,
                                          post_urls: List[str],
                                          target_genres: List[str],
                                          start_date: Optional[date] = None,
                                          end_date: Optional[date] = None) -> List[Dict]:
        """Filter posts by genre asynchronously."""
        logger.info(f"Filtering {len(post_urls)} posts for genres: {', '.join(target_genres)}")

        if start_date or end_date:
            date_range = f" from {start_date} to {end_date}" if start_date and end_date else \
                        f" from {start_date}" if start_date else f" until {end_date}"
            logger.info(f"Date range: {date_range}")

        # Create tasks for all posts
        tasks = []
        for post_url in post_urls:
            task = self.process_post(session, post_url, target_genres, start_date, end_date)
            tasks.append(task)

        # Process all posts concurrently
        logger.info(f"Processing {len(tasks)} posts concurrently...")
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out None results and exceptions
        matching_posts = []
        for i, result in enumerate(results):
            if isinstance(result, dict):
                matching_posts.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Error processing post {post_urls[i]}: {result}")

        logger.info(f"Found {len(matching_posts)} matching posts")
        return matching_posts

    def extract_genre_keywords(self, soup: BeautifulSoup) -> List[str]:
        """Extract genre keywords from a blog post."""
        genres = []

        try:
            # Get page content
            page_content = soup.get_text()

            # Look for genre patterns
            genre_patterns = GENRE_SELECTORS

            for pattern in genre_patterns:
                matches = re.findall(pattern, page_content, re.IGNORECASE)
                for match in matches:
                    genres.extend(self.extract_genres_from_text(match))

            # Always extract from full content
            genres.extend(self.extract_genres_from_text(page_content))

        except Exception as e:
            logger.warning(f"Error in genre extraction: {e}")

        return list(set(genres))

    def extract_genres_from_text(self, text: str) -> List[str]:
        """Extract genre keywords from text."""
        preferred_genres = ALL_EDM_GENRES

        found_genres = []
        text_lower = text.lower()

        for genre in preferred_genres:
            if genre in text_lower:
                found_genres.append(genre)

        return found_genres

    def extract_download_links(self, soup: BeautifulSoup, post_url: str) -> List[str]:
        """Extract download links from a blog post."""
        download_links = []
        seen_links = set()

        # Find all links on the page
        links = soup.find_all('a', href=True)

        for link in links:
            href = link.get('href')
            if href:
                # Check if it matches download patterns
                for pattern in self.download_patterns:
                    if re.search(pattern, href, re.IGNORECASE):
                        full_url = urljoin(post_url, href)
                        if full_url not in seen_links:
                            download_links.append(full_url)
                            seen_links.add(full_url)

        return download_links

    def extract_post_title(self, soup: BeautifulSoup) -> str:
        """Extract the title of a blog post."""
        selectors = TITLE_SELECTORS

        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                title = element.get_text().strip()
                if title:
                    return title

        return "Unknown Title"

    def extract_post_date(self, soup: BeautifulSoup, post_url: str) -> Optional[date]:
        """Extract the publication date of a blog post."""
        # Try URL-based extraction first
        url_patterns = URL_DATE_PATTERNS

        for pattern in url_patterns:
            match = re.search(pattern, post_url)
            if match:
                try:
                    year, month, day = match.groups()
                    return date(int(year), int(month), int(day))
                except ValueError:
                    continue

        # Try HTML selectors
        selectors = DATE_SELECTORS

        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                date_text = element.get_text().strip()
                parsed_date = self.parse_date_string(date_text)
                if parsed_date:
                    return parsed_date

        return None

    def parse_date_string(self, date_text: str) -> Optional[date]:
        """Parse various date string formats into a date object."""
        if not date_text:
            return None

        # Clean up text (handle newlines in "Nov\n21\n2025" format)
        date_text = re.sub(r'\s+', ' ', date_text.strip())

        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(date_text, fmt).date()
            except ValueError:
                continue

        # Try fuzzy parsing for "Nov 21 2025"
        try:
            return datetime.strptime(date_text, "%b %d %Y").date()
        except ValueError:
            pass

        return None

    async def save_results_async(self, matching_posts: List[Dict]):
        """Save results to file asynchronously."""
        async with asyncio.Lock():
            with open(self.output_file, 'w', encoding=DEFAULT_ENCODING) as f:
                f.write(f"EDM Music Download Links (Async) - Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
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

    async def run(self, target_genres: List[str], max_pages: int = DEFAULT_MAX_PAGES,
                  start_date: Optional[date] = None, end_date: Optional[date] = None) -> List[Dict]:
        """
        Run the async scraper.

        Args:
            target_genres: List of genres to search for
            max_pages: Maximum number of pages to scan
            start_date: Start date for filtering
            end_date: End date for filtering

        Returns:
            List of dictionaries with results
        """
        async with self.create_session() as session:
            # 1. Find post URLs
            post_urls = await self.find_blog_posts_async(session, max_pages)

            if not post_urls:
                logger.warning("No posts found to process")
                return []

            # 2. Process posts
            results = await self.filter_posts_by_genre_async(
                session, post_urls, target_genres, start_date, end_date
            )

            # Save results
            await self.save_results_async(results)

            return results

    async def scrape_website(self, max_pages: int = DEFAULT_MAX_PAGES, start_date=None, end_date=None) -> List[Dict]:
        """
        Alias for run method to match synchronous interface.

        Args:
            max_pages: Maximum number of pages to scan
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            List of dictionaries containing post details
        """
        # Use preferred_genres if available, otherwise use all genres
        target_genres = self.preferred_genres if self.preferred_genres else ALL_EDM_GENRES

        matching_posts = await self.run(target_genres, max_pages, start_date, end_date)
        # Save results
        await self.save_results_async(matching_posts)

        return matching_posts


def main():
    """Main entry point for async scraper."""
    parser = argparse.ArgumentParser(description='Async EDM blog scraper')
    parser.add_argument('url', help='Base URL of the blog site')
    parser.add_argument('--genres', nargs='+',
                        default=['house', 'progressive house', 'melodic', 'indie dance', 'bass house'],
                        help='Genre keywords to search for')
    parser.add_argument('--output', default='async_download_links.txt',
                        help='Output file name')
    parser.add_argument('--max-pages', type=int, default=DEFAULT_MAX_PAGES,
                        help='Maximum pages to search')
    parser.add_argument('--max-concurrent', type=int, default=MAX_CONCURRENT_REQUESTS,
                        help='Maximum concurrent requests')
    parser.add_argument('--start-date',
                        help='Start date for filtering (YYYY-MM-DD format)')
    parser.add_argument('--end-date',
                        help='End date for filtering (YYYY-MM-DD format)')

    args = parser.parse_args()

    # Parse dates
    start_date = None
    end_date = None

    if args.start_date:
        try:
            start_date = datetime.strptime(args.start_date, '%Y-%m-%d').date()
        except ValueError:
            logger.error("Invalid start date format. Use YYYY-MM-DD")
            return

    if args.end_date:
        try:
            end_date = datetime.strptime(args.end_date, '%Y-%m-%d').date()
        except ValueError:
            logger.error("Invalid end date format. Use YYYY-MM-DD")
            return

    # Create and run scraper
    scraper = AsyncMusicBlogScraper(args.url, args.output, args.max_concurrent)

    logger.info(f"Starting async scraper for {args.url}")
    logger.info(f"Max concurrent requests: {args.max_concurrent}")

    # Run async scraper
    asyncio.run(scraper.run(args.genres, args.max_pages, start_date, end_date))


if __name__ == "__main__":
    main()
