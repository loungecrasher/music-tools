"""Repository interfaces for data access."""

from .cache_repository import CacheRepository
from .config_repository import ConfigRepository

__all__ = ['CacheRepository', 'ConfigRepository']
