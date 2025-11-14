"""
Version detection modules.
"""

from .github_detector import GitHubDetector
from .pypi_detector import PyPIDetector

__all__ = ["GitHubDetector", "PyPIDetector"]

