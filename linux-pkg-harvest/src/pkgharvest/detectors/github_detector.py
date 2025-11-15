"""
GitHub version detector.
"""

from typing import Optional, Dict, Any
import logging
import re
from pkgharvest.utils.http_client import HttpClient

logger = logging.getLogger(__name__)


class GitHubDetector:
    """Detect package versions from GitHub repositories."""

    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub detector.

        Args:
            token: Optional GitHub API token for authenticated requests
        """
        self.http_client = HttpClient()
        self.token = token
        self.base_url = "https://api.github.com"
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_latest_version(self, repo: str) -> Optional[str]:
        """
        Get the latest version from a GitHub repository.

        Args:
            repo: Repository in format "owner/repo"

        Returns:
            Latest version string or None if not found
        """
        try:
            url = f"{self.base_url}/repos/{repo}/releases/latest"
            headers = {}
            if self.token:
                headers["Authorization"] = f"token {self.token}"

            response = self.http_client.get(url, headers=headers)
            if response and response.get("tag_name"):
                # Remove 'v' prefix if present
                version = response["tag_name"].lstrip("v")
                return version
        except Exception as e:
            self.logger.error(f"Error getting latest version from GitHub {repo}: {e}")

        return None

    def get_all_versions(self, repo: str) -> list[str]:
        """
        Get all versions/releases from a GitHub repository.

        Args:
            repo: Repository in format "owner/repo"

        Returns:
            List of version strings
        """
        versions = []
        try:
            url = f"{self.base_url}/repos/{repo}/releases"
            headers = {}
            if self.token:
                headers["Authorization"] = f"token {self.token}"

            response = self.http_client.get(url, headers=headers)
            if isinstance(response, list):
                for release in response:
                    if release.get("tag_name"):
                        version = release["tag_name"].lstrip("v")
                        versions.append(version)
        except Exception as e:
            self.logger.error(f"Error getting versions from GitHub {repo}: {e}")

        return versions

    def get_release_date(self, repo: str, version: str) -> Optional[str]:
        """
        Get release date for a specific version.

        Args:
            repo: Repository in format "owner/repo"
            version: Version string

        Returns:
            Release date as ISO string or None if not found
        """
        try:
            url = f"{self.base_url}/repos/{repo}/releases/tags/{version}"
            headers = {}
            if self.token:
                headers["Authorization"] = f"token {self.token}"

            response = self.http_client.get(url, headers=headers)
            if response and response.get("published_at"):
                return response["published_at"]
        except Exception as e:
            self.logger.error(f"Error getting release date from GitHub {repo} for {version}: {e}")

        return None

    def detect_from_readme(self, repo: str) -> Optional[str]:
        """
        Attempt to detect version from repository README.

        Args:
            repo: Repository in format "owner/repo"

        Returns:
            Detected version string or None
        """
        try:
            url = f"https://raw.githubusercontent.com/{repo}/main/README.md"
            content = self.http_client.get_text(url)
            if content:
                # Simple pattern matching for version numbers
                patterns = [
                    r"version[:\s]+([\d.]+)",
                    r"v([\d.]+)",
                    r"([\d]+\.[\d]+\.[\d]+)",
                ]
                for pattern in patterns:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        return match.group(1)
        except Exception as e:
            self.logger.warning(f"Error detecting version from README: {e}")

        return None

    def get_repo_language(self, repo: str) -> Optional[str]:
        """
        Get the primary language of a GitHub repository.

        Args:
            repo: Repository in format "owner/repo"

        Returns:
            Language string (e.g. 'Python') or None
        """
        try:
            url = f"{self.base_url}/repos/{repo}"
            headers = {}
            if self.token:
                headers["Authorization"] = f"token {self.token}"

            response = self.http_client.get(url, headers=headers)
            if response and response.get("language"):
                return response.get("language")
        except Exception as e:
            self.logger.warning(f"Error getting repo language from GitHub {repo}: {e}")

        return None

