"""
Configuration management for the EDM Music Blog Scraper.
Handles settings, validation, defaults, and scraping constants.
"""

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

# ==========================================
# Scraping Constants (Reconstructed)
# ==========================================

# Request Settings
REQUEST_TIMEOUT = 30
REQUEST_DELAY = 1.0
MAX_RETRIES = 3
BACKOFF_FACTOR = 0.5
MAX_DELAY = 10.0
RATE_LIMIT_MIN_DELAY = 1.0
RATE_LIMIT_MAX_DELAY = 3.0
MAX_CONCURRENT_REQUESTS = 5
MAX_CONCURRENT_REQUESTS_PER_HOST = 3
CHUNK_SIZE = 8192
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
USER_AGENTS = [
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
]
VALID_HOSTS = [
    'sharing-db.club', 'edmblog.com', 'nfile.cc', 'novafile.org',
    'mediafire.com', 'mega.nz', 'dropbox.com', 'google.com',
    'drive.google.com', 'zippyshare.com', 'rapidshare.com',
    'depositfiles.com', 'soundcloud.com'
]

# Pagination & Limits
DEFAULT_MAX_PAGES = 10
MAX_PAGES_LIMIT = 100
MAX_EMPTY_PAGES = 5
POSTS_PER_PAGE_ESTIMATE = 10
DEFAULT_OUTPUT_FILE = "scraper_results.txt"
DEFAULT_ENCODING = "utf-8"
MAX_URL_LENGTH = 2048
MAX_TITLE_LENGTH = 500
MAX_GENRE_LENGTH = 100
GROUP_SIZE = 20

# Genres
DEFAULT_GENRES = [
    'house', 'progressive house', 'melodic', 'indie dance', 'bass house',
    'organic house', 'drum and bass', 'uk garage', 'electro pop', 'nu disco',
    'funky', 'deep house', 'tech house', 'dance', 'afro house', 'brazilian',
    'latin', 'electronica', 'ambient'
]
ALL_EDM_GENRES = DEFAULT_GENRES + ['techno', 'trance', 'minimal', 'dubstep', 'trap', 'hardstyle']

# CSS selectors for finding blog posts
BLOG_POST_SELECTORS = [
    'article a[href*="/"]',
    '.post-title a',
    '.entry-title a',
    'h2 a',
    'h3 a',
    '.blog-post a',
    '.post a',
    'a[href*="/20"]',  # Links with year
    'a[href*="/post"]',
    'a[href*="/article"]',
    'a[href*="/blog"]',
    '.title a',
    '.headline a',
    'div.post h2 a',  # Specific for sharing-db.club
]

# CSS selectors for finding genre information
GENRE_SELECTORS = [
    '.genre', '.tags', '.categories', '.post-tags',
    '.entry-tags', '.post-categories', '.meta-categories',
    '[class*="genre"]', '[class*="tag"]', '[class*="category"]',
    '.post-meta', '.entry-meta', '.meta',
    '.cat-links', '.tags-links', '.postmeta', '.metadata'
]

# CSS selectors for finding post titles
TITLE_SELECTORS = [
    '.post-title', '.entry-title', '.title',
    '[class*="title"]', '.headline',
    'h2.title', 'h2.entry-title', 'h3.post-title',
    'div.post h2',  # Specific for sharing-db.club
    'h2', 'h1', 'title'
]

# Date extraction settings
DATE_SELECTORS = [
    '.post-date', '.entry-date', '.date', '.published',
    '.post-meta .date', '.entry-meta .date', '.meta .date',
    '[class*="date"]', '[class*="time"]', 'time',
    '.post-info .date', '.article-date', '.blog-date'
]

META_DATE_SELECTORS = [
    'meta[property="article:published_time"]',
    'meta[name="date"]',
    'meta[name="publish_date"]',
    'meta[property="og:updated_time"]'
]

# Date patterns to search for in page text
DATE_PATTERNS = [
    re.compile(r'(\d{4}-\d{2}-\d{2})'),  # YYYY-MM-DD
    re.compile(r'(\d{2}/\d{2}/\d{4})'),  # MM/DD/YYYY
    re.compile(r'(\d{2}-\d{2}-\d{4})'),  # MM-DD-YYYY
    re.compile(r'(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4})', re.IGNORECASE),  # DD Month YYYY
    re.compile(r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4})', re.IGNORECASE),  # Month DD, YYYY
]

# URL date patterns
URL_DATE_PATTERNS = [
    re.compile(r'/(\d{4})/(\d{2})/(\d{2})/'),  # /2024/01/15/
    re.compile(r'/(\d{4})-(\d{2})-(\d{2})/'),  # /2024-01-15/
    re.compile(r'/(\d{4})_(\d{2})_(\d{2})/'),  # /2024_01_15/
    re.compile(r'(\d{4})(\d{2})(\d{2})'),      # 20240115
]

# Date formats to try when parsing
DATE_FORMATS = [
    '%Y-%m-%d',           # 2024-01-15
    '%Y/%m/%d',           # 2024/01/15
    '%m/%d/%Y',           # 01/15/2024
    '%d/%m/%Y',           # 15/01/2024
    '%m-%d-%Y',           # 01-15-2024
    '%d-%m-%Y',           # 15-01-2024
    '%B %d, %Y',          # January 15, 2024
    '%B %d %Y',           # January 15 2024
    '%b %d, %Y',          # Jan 15, 2024
    '%b %d %Y',           # Jan 15 2024
    '%d %B %Y',           # 15 January 2024
    '%d %b %Y',           # 15 Jan 2024
    '%Y-%m-%dT%H:%M:%S',  # 2024-01-15T14:30:25
    '%Y-%m-%dT%H:%M:%SZ',  # 2024-01-15T14:30:25Z
]

# URL Patterns
SKIP_URL_PATTERNS = [
    '/tag/', '/category/', '/author/', '/page/', '/feed/', '/comments/',
    '/about', '/contact', '/privacy', '/terms', '/rss', '/sitemap',
    '/search', '/login', '/register', '/admin', '/wp-admin',
    '/reply', '/trackback', '/pingback',
]

POST_URL_INDICATORS = [
    '/20', '/post', '/article', '/blog', '/entry',
    '/track/', '/release/', '/album/', '/ep/', '/remix/', 'sharing-db.club/'
]

PAGINATION_PATTERNS = [
    re.compile(r'/page/(\d+)'),
    re.compile(r'\?paged=(\d+)'),
    re.compile(r'/\?page=(\d+)')
]

# Download Patterns
DOWNLOAD_PATTERNS = [
    re.compile(r'zippyshare\.com', re.I),
    re.compile(r'krakenfiles\.com', re.I),
    re.compile(r'we\.tl', re.I),
    re.compile(r'wetransfer\.com', re.I),
    re.compile(r'drive\.google\.com', re.I),
    re.compile(r'mega\.nz', re.I),
    re.compile(r'mediafire\.com', re.I),
    re.compile(r'sendspace\.com', re.I),
    re.compile(r'turbobit\.net', re.I),
    re.compile(r'rapidgator\.net', re.I),
    re.compile(r'uploaded\.net', re.I),
    re.compile(r'hybeddit\.com', re.I),
    re.compile(r'hypeddit\.com', re.I),
    re.compile(r'nfile\.cc', re.I),
    re.compile(r'novafile\.org', re.I),
    re.compile(r'dropbox\.com', re.I),
    re.compile(r'google\.com', re.I),
    re.compile(r'rapidshare\.com', re.I),
    re.compile(r'depositfiles\.com', re.I),
    re.compile(r'soundcloud\.com', re.I)
]

RELEASE_IDENTIFIER_PATTERNS = [
    re.compile(r'([A-Z0-9]+-\d+)'),  # Catalog numbers
    re.compile(r'\[([A-Z0-9]+)\]'),   # Bracketed IDs
    re.compile(r'/(\d+)_'),  # Number followed by underscore
    re.compile(r'/([a-zA-Z0-9-]+)_[a-zA-Z0-9-]+$'),  # Alphanumeric before last underscore
]

# ==========================================
# New Configuration Classes
# ==========================================


@dataclass
class ScraperSettings:
    """Data class to hold scraper settings."""
    url: str = ""
    scraper_type: str = "standard"  # 'standard' or 'specialized'
    genres: List[str] = field(default_factory=list)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    output_filename: str = ""
    save_json: bool = False
    max_pages: int = 10

    @property
    def is_valid(self) -> bool:
        """Check if essential settings are populated."""
        return bool(self.url and self.output_filename)


class ScraperConfig:
    """Manages configuration options and validation."""

    DEFAULT_GENRES = DEFAULT_GENRES

    @staticmethod
    def get_quick_date_ranges() -> Dict[str, Optional[date]]:
        """Get common date range presets."""
        today = datetime.now().date()
        return {
            'Last 7 days': today - timedelta(days=7),
            'Last 30 days': today - timedelta(days=30),
            'Last 3 months': today - timedelta(days=90),
            'Last 6 months': today - timedelta(days=180),
            'This year': date(today.year, 1, 1),
            'Last year': date(today.year - 1, 1, 1),
            'Custom range': None
        }

    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate blog URL."""
        if not url:
            return False
        # Basic validation, could use regex or urllib
        return url.startswith('http://') or url.startswith('https://')

    @staticmethod
    def validate_date_range(start_date: Optional[date], end_date: Optional[date]) -> Tuple[bool, str]:
        """Validate date range."""
        if start_date and end_date and start_date > end_date:
            return False, "Start date cannot be after end date."
        return True, ""

    @staticmethod
    def get_default_filename() -> str:
        """Generate a default filename with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"edm_scraper_results_{timestamp}.txt"

    @staticmethod
    def calculate_recommended_pages(start_date: Optional[date], end_date: Optional[date]) -> int:
        """Calculate recommended pages based on date range."""
        if not start_date:
            return 10  # Default if no start date

        # Calculate days difference
        if not end_date:
            end_date = datetime.now().date()

        days_diff = (end_date - start_date).days

        # Estimate: ~10 posts per page, maybe 1-2 days per page depending on blog volume
        # This is a rough heuristic
        if days_diff <= 7:
            return 3
        elif days_diff <= 30:
            return 10
        elif days_diff <= 90:
            return 25
        elif days_diff <= 180:
            return 50
        else:
            return 100
