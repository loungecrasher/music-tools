"""
Base CLI class for Music Tools applications.
"""
import sys
import logging
from abc import ABC, abstractmethod
from typing import Optional

logger = logging.getLogger('music_tools_common.cli')


class BaseCLI(ABC):
    """Base class for CLI applications."""
    
    def __init__(self, name: str, version: str = "1.0.0"):
        self.name = name
        self.version = version
        self.logger = logging.getLogger(name)
    
    @abstractmethod
    def run(self) -> int:
        """Run the CLI application."""
        pass
    
    def error(self, message: str, exit_code: int = 1) -> None:
        """Print error and exit."""
        self.logger.error(message)
        sys.exit(exit_code)
    
    def info(self, message: str) -> None:
        """Print info message."""
        self.logger.info(message)
