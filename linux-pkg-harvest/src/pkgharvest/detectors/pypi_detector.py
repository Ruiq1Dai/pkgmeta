"""
PyPI version detector.
"""

from typing import Optional, Dict, Any, List
import logging
from pkgharvest.utils.http_client import HttpClient

logger = logging.getLogger(__name__)


class PyPIDetector:
    """Detect package versions from PyPI."""

    def __init__(self):
        """Initialize PyPI detector."""
        self.http_client = HttpClient()
        self.base_url = "https://pypi.org/pypi"
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_latest_version(self, package_name: str) -> Optional[str]:
        """
        Get the latest version of a PyPI package.

        Args:
            package_name: Name of the PyPI package

        Returns:
            Latest version string or None if not found
        """
        try:
            url = f"{self.base_url}/{package_name}/json"
            response = self.http_client.get(url)
            if response and "info" in response:
                return response["info"].get("version")
        except Exception as e:
            self.logger.error(f"Error getting latest version from PyPI for {package_name}: {e}")

        return None

    def get_all_versions(self, package_name: str) -> List[str]:
        """
        Get all versions of a PyPI package.

        Args:
            package_name: Name of the PyPI package

        Returns:
            List of version strings
        """
        versions = []
        try:
            url = f"{self.base_url}/{package_name}/json"
            response = self.http_client.get(url)
            if response and "releases" in response:
                versions = list(response["releases"].keys())
                # Sort versions (simple string sort, can be enhanced)
                versions.sort(reverse=True)
        except Exception as e:
            self.logger.error(f"Error getting versions from PyPI for {package_name}: {e}")

        return versions

    def get_release_date(self, package_name: str, version: str) -> Optional[str]:
        """
        Get release date for a specific version.

        Args:
            package_name: Name of the PyPI package
            version: Version string

        Returns:
            Release date as ISO string or None if not found
        """
        try:
            url = f"{self.base_url}/{package_name}/{version}/json"
            response = self.http_client.get(url)
            if response and "urls" in response:
                urls = response["urls"]
                if urls and len(urls) > 0:
                    # Get upload time from first URL entry
                    upload_time = urls[0].get("upload_time")
                    return upload_time
        except Exception as e:
            self.logger.error(f"Error getting release date from PyPI for {package_name} {version}: {e}")

        return None

    def get_package_info(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        Get full package information from PyPI.

        Args:
            package_name: Name of the PyPI package

        Returns:
            Dictionary containing package information or None
        """
        try:
            url = f"{self.base_url}/{package_name}/json"
            response = self.http_client.get(url)
            if response:
                info = response.get("info", {})
                return {
                    "name": info.get("name"),
                    "version": info.get("version"),
                    "summary": info.get("summary"),
                    "description": info.get("description"),
                    "home_page": info.get("home_page"),
                    "author": info.get("author"),
                    "license": info.get("license"),
                }
        except Exception as e:
            self.logger.error(f"Error getting package info from PyPI for {package_name}: {e}")

        return None

