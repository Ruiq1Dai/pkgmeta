"""
Base collector class for package information harvesting.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """Base class for all package collectors."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the collector.

        Args:
            config: Configuration dictionary for the collector
        """
        self.config = config or {}
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def collect_packages(self, version: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Collect package information from the repository.

        Args:
            version: Optional version identifier for the distribution

        Returns:
            List of package dictionaries containing package information
        """
        pass

    @abstractmethod
    def get_package_info(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information for a specific package.

        Args:
            package_name: Name of the package

        Returns:
            Dictionary containing package information or None if not found
        """
        pass

    @abstractmethod
    def get_repository_url(self, version: Optional[str] = None) -> str:
        """
        Get the repository URL for the distribution.

        Args:
            version: Optional version identifier

        Returns:
            Repository URL string
        """
        pass

    def validate_config(self) -> bool:
        """
        Validate the collector configuration.

        Returns:
            True if configuration is valid, False otherwise
        """
        return True

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass

