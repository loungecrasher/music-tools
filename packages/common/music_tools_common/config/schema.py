"""
Configuration schemas for Music Tools.
Uses Pydantic for validation and type safety.
"""
from typing import Optional
from pydantic import BaseModel, Field, EmailStr, HttpUrl


class SpotifyConfig(BaseModel):
    """Spotify API configuration."""

    client_id: str = Field(..., description="Spotify Client ID")
    client_secret: str = Field(..., description="Spotify Client Secret")
    redirect_uri: str = Field(
        default="http://localhost:8888/callback",
        description="OAuth redirect URI"
    )
    scope: str = Field(
        default="playlist-read-private playlist-modify-private playlist-modify-public user-library-read",
        description="OAuth scopes"
    )

    class Config:
        frozen = True  # Make immutable


class DeezerConfig(BaseModel):
    """Deezer API configuration."""

    email: str = Field(..., description="Deezer account email")
    user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        description="User agent for API requests"
    )

    class Config:
        frozen = True


class AnthropicConfig(BaseModel):
    """Anthropic Claude API configuration."""

    api_key: str = Field(..., description="Anthropic API key")
    model: str = Field(
        default="claude-3-5-sonnet-20241022",
        description="Claude model to use"
    )
    max_tokens: int = Field(
        default=1024,
        description="Maximum tokens per request"
    )

    class Config:
        frozen = True


class DatabaseConfig(BaseModel):
    """Database configuration."""

    path: str = Field(
        default="~/.music_tools/data/music_tools.db",
        description="SQLite database path"
    )
    backup_enabled: bool = Field(
        default=True,
        description="Enable automatic backups"
    )
    backup_interval: int = Field(
        default=86400,
        description="Backup interval in seconds (default: 24 hours)"
    )

    class Config:
        frozen = True


class CacheConfig(BaseModel):
    """Cache configuration."""

    enabled: bool = Field(default=True, description="Enable caching")
    ttl: int = Field(default=3600, description="Cache TTL in seconds")
    max_size: int = Field(default=1000, description="Maximum cache entries")
    path: str = Field(
        default="~/.music_tools/cache",
        description="Cache directory path"
    )

    class Config:
        frozen = True


class ConfigSchema(BaseModel):
    """Overall configuration schema."""

    spotify: Optional[SpotifyConfig] = None
    deezer: Optional[DeezerConfig] = None
    anthropic: Optional[AnthropicConfig] = None
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    cache: CacheConfig = Field(default_factory=CacheConfig)

    class Config:
        frozen = True
