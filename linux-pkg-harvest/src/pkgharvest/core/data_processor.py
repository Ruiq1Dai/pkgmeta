"""
Data processing module for package information.
"""

from typing import Dict, List, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class DataProcessor:
    """Process and transform package data."""

    def __init__(self):
        """Initialize the data processor."""
        self.logger = logging.getLogger(self.__class__.__name__)

    def normalize_package_data(self, package_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize package data to a standard format.

        Args:
            package_data: Raw package data dictionary

        Returns:
            Normalized package data dictionary
        """
        normalized = {
            "name": package_data.get("name", ""),
            "version": package_data.get("version", ""),
            "release": package_data.get("release", ""),
            "arch": package_data.get("arch", ""),
            "description": package_data.get("description", ""),
            "dependencies": package_data.get("dependencies", []),
            "source_url": package_data.get("source_url", ""),
            "timestamp": datetime.utcnow().isoformat(),
        }
        return normalized

    def filter_packages(
        self,
        packages: List[Dict[str, Any]],
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Filter packages based on criteria.

        Args:
            packages: List of package dictionaries
            filters: Dictionary of filter criteria

        Returns:
            Filtered list of packages
        """
        if not filters:
            return packages

        filtered = packages
        if "name_pattern" in filters:
            import re
            pattern = re.compile(filters["name_pattern"])
            filtered = [pkg for pkg in filtered if pattern.search(pkg.get("name", ""))]

        if "min_version" in filters:
            # Simple version comparison - can be enhanced
            filtered = [
                pkg for pkg in filtered
                if self._compare_versions(pkg.get("version", ""), filters["min_version"]) >= 0
            ]

        return filtered

    def _compare_versions(self, version1: str, version2: str) -> int:
        """
        Compare two version strings.

        Args:
            version1: First version string
            version2: Second version string

        Returns:
            -1 if version1 < version2, 0 if equal, 1 if version1 > version2
        """
        try:
            from packaging import version
            v1 = version.parse(version1)
            v2 = version.parse(version2)
            if v1 < v2:
                return -1
            elif v1 > v2:
                return 1
            return 0
        except Exception as e:
            self.logger.warning(f"Error comparing versions {version1} and {version2}: {e}")
            return 0

    def aggregate_statistics(self, packages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate statistics from package data.

        Args:
            packages: List of package dictionaries

        Returns:
            Dictionary containing statistics
        """
        stats = {
            "total_packages": len(packages),
            "unique_versions": len(set(pkg.get("version", "") for pkg in packages)),
            "architectures": list(set(pkg.get("arch", "") for pkg in packages if pkg.get("arch"))),
        }
        return stats

    def export_to_json(self, packages: List[Dict[str, Any]], filepath: str) -> bool:
        """
        Export package data to JSON file.

        Args:
            packages: List of package dictionaries
            filepath: Output file path

        Returns:
            True if successful, False otherwise
        """
        try:
            import json
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(packages, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            self.logger.error(f"Error exporting to JSON: {e}")
            return False

    def export_to_csv(self, packages: List[Dict[str, Any]], filepath: str) -> bool:
        """
        Export package data to CSV file.

        Args:
            packages: List of package dictionaries
            filepath: Output file path

        Returns:
            True if successful, False otherwise
        """
        try:
            import csv
            if not packages:
                return False

            fieldnames = packages[0].keys()
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(packages)
            return True
        except Exception as e:
            self.logger.error(f"Error exporting to CSV: {e}")
            return False

    def save_to_database(
        self,
        packages: List[Dict[str, Any]],
        db_manager: Any,
        collector_name: str,
        distribution_version: Optional[str] = None,
        repository_id: Optional[int] = None
    ) -> int:
        """
        Save packages to database.

        Args:
            packages: List of package data dictionaries
            db_manager: DatabaseManager instance
            collector_name: Name of the collector
            distribution_version: Optional distribution version
            repository_id: Optional repository ID

        Returns:
            Number of packages saved
        """
        try:
            # Add collector_name and distribution_version to each package
            for package in packages:
                package["collector_name"] = collector_name
                if distribution_version:
                    package["distribution_version"] = distribution_version

            saved_count = db_manager.save_packages_batch(packages, repository_id)
            self.logger.info(f"Saved {saved_count}/{len(packages)} packages to database")
            return saved_count
        except Exception as e:
            self.logger.error(f"Error saving to database: {e}")
            return 0

