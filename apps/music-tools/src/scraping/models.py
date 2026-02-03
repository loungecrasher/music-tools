#!/usr/bin/env python3
"""
Pydantic models for data validation in the EDM Music Blog Scraper.
"""

import logging
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, ValidationInfo, field_validator

logger = logging.getLogger(__name__)


class FileFormat(str, Enum):
    """Supported audio file formats."""

    FLAC = "flac"
    MP3 = "mp3"
    WAV = "wav"
    M4A = "m4a"
    AAC = "aac"
    ZIP = "zip"
    RAR = "rar"
    SEVEN_Z = "7z"


class AudioQuality(str, Enum):
    """Audio quality levels."""

    LOSSLESS = "lossless"
    HIGH = "320kbps"
    MEDIUM = "256kbps"
    LOW = "128kbps"
    UNKNOWN = "unknown"


class DownloadLink(BaseModel):
    """Model for a download link."""

    url: HttpUrl
    format: Optional[FileFormat] = None
    quality: Optional[AudioQuality] = AudioQuality.UNKNOWN
    size_mb: Optional[float] = None
    host: Optional[str] = None

    @field_validator("host", mode="before")
    @classmethod
    def extract_host(cls, v: Any, info: ValidationInfo) -> Any:
        """Extract host from URL if not provided."""
        if v is None and "url" in info.data:
            from urllib.parse import urlparse

            return urlparse(str(info.data["url"])).netloc
        return v

    @field_validator("format", mode="before")
    @classmethod
    def detect_format(cls, v: Any, info: ValidationInfo) -> Any:
        """Detect format from URL if not provided."""
        if v is None and "url" in info.data:
            url_str = str(info.data["url"]).lower()
            for fmt in FileFormat:
                if f".{fmt.value}" in url_str:
                    return fmt
        return v

    @field_validator("quality", mode="before")
    @classmethod
    def detect_quality(cls, v: Any, info: ValidationInfo) -> Any:
        """Detect quality from URL if not provided."""
        if v is None and "url" in info.data:
            url_str = str(info.data["url"]).lower()
            if "flac" in url_str or "lossless" in url_str:
                return AudioQuality.LOSSLESS
            elif "320" in url_str:
                return AudioQuality.HIGH
            elif "256" in url_str:
                return AudioQuality.MEDIUM
            elif "128" in url_str:
                return AudioQuality.LOW
        return v

    def to_dict(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "url": str(self.url),
            "format": self.format.value if self.format else None,
            "quality": self.quality.value if self.quality else None,
            "size_mb": self.size_mb,
            "host": self.host,
        }


class Genre(BaseModel):
    """Model for music genre."""

    name: str = Field(..., min_length=1, max_length=100)
    weight: Optional[int] = Field(default=1, ge=1, le=10)
    aliases: List[str] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def normalize_name(cls, v: str) -> str:
        """Normalize genre name."""
        return v.lower().strip()

    @field_validator("aliases", mode="before")
    @classmethod
    def normalize_aliases(cls, v: Any) -> Any:
        """Normalize aliases."""
        if isinstance(v, list):
            return [alias.lower().strip() for alias in v]
        return v

    def matches(self, text: str) -> bool:
        """Check if genre matches text."""
        text_lower = text.lower()
        if self.name in text_lower:
            return True
        return any(alias in text_lower for alias in self.aliases)


class BlogPost(BaseModel):
    """Model for a blog post."""

    url: HttpUrl
    title: str = Field(..., min_length=1, max_length=500)
    post_date: Optional[date] = None
    genres: List[str] = Field(default_factory=list)
    matching_genres: List[str] = Field(default_factory=list)
    download_links: List[DownloadLink] = Field(default_factory=list)
    score: Optional[int] = Field(default=0, ge=0)

    @field_validator("genres", "matching_genres")
    @classmethod
    def normalize_genres(cls, v: List[str]) -> List[str]:
        """Normalize genre lists."""
        return [genre.lower().strip() for genre in v]

    @field_validator("post_date", mode="before")
    @classmethod
    def parse_date(cls, v: Any) -> Any:
        """Parse date from various formats."""
        if v is None:
            return None
        if isinstance(v, date):
            return v
        if isinstance(v, str):
            # Try ISO format first
            try:
                return datetime.fromisoformat(v).date()
            except (ValueError, TypeError):
                pass
            # Try common formats
            date_formats = [
                "%Y-%m-%d",
                "%Y/%m/%d",
                "%m/%d/%Y",
                "%d/%m/%Y",
                "%m-%d-%Y",
                "%d-%m-%Y",
                "%B %d, %Y",
                "%B %d %Y",
                "%b %d, %Y",
                "%b %d %Y",
                "%d %B %Y",
                "%d %b %Y",
            ]
            for fmt in date_formats:
                try:
                    return datetime.strptime(v, fmt).date()
                except (ValueError, TypeError):
                    continue
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = self.model_dump()
        # Convert date to ISO format string
        if data.get("post_date"):
            data["post_date"] = data["post_date"].isoformat()
        # Convert download links to dicts using their to_dict method
        data["download_links"] = [link.to_dict() for link in self.download_links]
        # Convert URL to string
        data["url"] = str(data["url"])
        return data


class ScraperConfig(BaseModel):
    """Configuration for scraper."""

    base_url: HttpUrl
    output_file: str = Field(default="download_links.txt", min_length=1)
    max_pages: int = Field(default=10, ge=1, le=100)
    max_concurrent: int = Field(default=5, ge=1, le=20)
    target_genres: List[str] = Field(default_factory=list)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    save_json: bool = Field(default=False)

    @field_validator("output_file")
    @classmethod
    def validate_output_file(cls, v: str) -> str:
        """Ensure output file has proper extension."""
        if not v.endswith((".txt", ".json")):
            return v + ".txt"
        return v

    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, v: Any, info: ValidationInfo) -> Any:
        """Ensure end date is after start date."""
        if v and "start_date" in info.data and info.data["start_date"]:
            if v < info.data["start_date"]:
                raise ValueError("End date must be after start date")
        return v

    @field_validator("target_genres")
    @classmethod
    def normalize_target_genres(cls, v: List[str]) -> List[str]:
        """Normalize target genres."""
        return [genre.lower().strip() for genre in v]


class ScraperResult(BaseModel):
    """Result from scraping operation."""

    metadata: Dict[str, Any] = Field(default_factory=dict)
    posts: List[BlogPost] = Field(default_factory=list)
    total_posts: int = Field(default=0)
    total_links: int = Field(default=0)
    execution_time: Optional[float] = None
    errors: List[str] = Field(default_factory=list)

    @field_validator("total_posts", mode="before")
    @classmethod
    def calculate_total_posts(cls, v: Any, info: ValidationInfo) -> Any:
        """Calculate total posts if not provided."""
        if v == 0 and "posts" in info.data:
            return len(info.data["posts"])
        return v

    @field_validator("total_links", mode="before")
    @classmethod
    def calculate_total_links(cls, v: Any, info: ValidationInfo) -> Any:
        """Calculate total links if not provided."""
        if v == 0 and "posts" in info.data:
            return sum(len(post.download_links) for post in info.data["posts"])
        return v

    def add_post(self, post: BlogPost):
        """Add a post to results."""
        self.posts.append(post)
        self.total_posts = len(self.posts)
        self.total_links = sum(len(p.download_links) for p in self.posts)

    def to_json(self) -> Dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "metadata": {
                **self.metadata,
                "total_posts": self.total_posts,
                "total_links": self.total_links,
                "execution_time": self.execution_time,
                "errors": self.errors,
            },
            "posts": [post.to_dict() for post in self.posts],
        }


class LinkExtractionResult(BaseModel):
    """Result from link extraction."""

    total_links: int = Field(default=0, ge=0)
    unique_links: List[str] = Field(default_factory=list)
    quality_stats: Dict[str, int] = Field(default_factory=dict)
    host_stats: Dict[str, int] = Field(default_factory=dict)
    format_stats: Dict[str, int] = Field(default_factory=dict)

    @field_validator("total_links", mode="before")
    @classmethod
    def calculate_total(cls, v: Any, info: ValidationInfo) -> Any:
        """Calculate total if not provided."""
        if v == 0 and "unique_links" in info.data:
            return len(info.data["unique_links"])
        return v

    def add_link(self, link: str):
        """Add a link to results."""
        if link not in self.unique_links:
            self.unique_links.append(link)
            self.total_links = len(self.unique_links)
            self._update_stats(link)

    def _update_stats(self, link: str):
        """Update statistics for a link."""
        link_lower = link.lower()

        # Update quality stats
        if "flac" in link_lower or "lossless" in link_lower:
            self.quality_stats["flac"] = self.quality_stats.get("flac", 0) + 1
        elif "320" in link_lower:
            self.quality_stats["mp3_320"] = self.quality_stats.get("mp3_320", 0) + 1
        else:
            self.quality_stats["other"] = self.quality_stats.get("other", 0) + 1

        # Update host stats
        from urllib.parse import urlparse

        host = urlparse(link).netloc
        if host:
            self.host_stats[host] = self.host_stats.get(host, 0) + 1

        # Update format stats
        for fmt in FileFormat:
            if f".{fmt.value}" in link_lower:
                self.format_stats[fmt.value] = self.format_stats.get(fmt.value, 0) + 1
                break


# Validation functions for use in scrapers
def validate_url(url: str) -> Optional[HttpUrl]:
    """Validate and return a proper URL."""
    try:
        return HttpUrl(url)
    except Exception:
        return None


def validate_post_data(data: Dict[str, Any]) -> Optional[BlogPost]:
    """Validate post data and return BlogPost model."""
    try:
        # Convert download links to DownloadLink models
        if "download_links" in data and isinstance(data["download_links"], list):
            download_links = []
            for link in data["download_links"]:
                if isinstance(link, str):
                    try:
                        download_links.append(DownloadLink(url=link))
                    except (ValueError, TypeError) as e:
                        logger.debug(f"Skipping invalid URL: {link}, error: {e}")
                        continue
                elif isinstance(link, dict):
                    try:
                        download_links.append(DownloadLink(**link))
                    except (ValueError, TypeError) as e:
                        logger.debug(f"Skipping invalid link dict: {link}, error: {e}")
                        continue
            data["download_links"] = download_links

        return BlogPost(**data)
    except Exception as e:
        print(f"Validation error: {e}")
        return None


def create_genre_model(name: str, weight: int = 5, aliases: Optional[List[str]] = None) -> Genre:
    """Create a Genre model."""
    return Genre(name=name, weight=weight, aliases=aliases or [])


# Pre-defined genre models
PREFERRED_GENRES = [
    create_genre_model("house", 10, ["house music", "house mix"]),
    create_genre_model("progressive house", 10, ["prog house", "progressive"]),
    create_genre_model("melodic", 9, ["melodic house", "melodic techno"]),
    create_genre_model("indie dance", 9, ["indie", "indie electronic"]),
    create_genre_model("bass house", 9, ["basshouse", "bass house music"]),
    create_genre_model("organic house", 8, ["organic", "organic electronic"]),
    create_genre_model("drum and bass", 8, ["dnb", "drum n bass"]),
    create_genre_model("uk garage", 8, ["ukg", "garage", "speed garage"]),
    create_genre_model("electro pop", 8, ["electropop", "electronic pop"]),
    create_genre_model("nu disco", 8, ["nu-disco", "new disco"]),
    create_genre_model("funky", 7, ["funk", "funky house"]),
    create_genre_model("deep house", 7, ["deep", "deep house music"]),
    create_genre_model("tech house", 7, ["techhouse", "tech house music"]),
    create_genre_model("dance", 7, ["dance music", "electronic dance"]),
    create_genre_model("afro house", 7, ["afro", "african house"]),
    create_genre_model("brazilian", 6, ["brazil", "brazilian house"]),
    create_genre_model("latin", 6, ["latin house", "latin electronic"]),
    create_genre_model("electronica", 6, ["electronic", "electronica music"]),
    create_genre_model("ambient", 5, ["ambient music", "ambient electronic"]),
]
