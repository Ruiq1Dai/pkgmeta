"""
Data processing module for package information.
"""

from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import re

from pkgharvest.core.libyear_calculator import LibYearCalculator
from pkgharvest.detectors.github_detector import GitHubDetector
from pkgharvest.detectors.pypi_detector import PyPIDetector

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
            # Initialize detectors and calculators
            gh_detector = GitHubDetector()
            pypi_detector = PyPIDetector()
            ly_calc = LibYearCalculator()

            def parse_iso_to_datetime(iso_str: Optional[str]) -> Optional[datetime]:
                if not iso_str:
                    return None
                try:
                    # Handle common GitHub/PyPI formats like '2020-01-01T00:00:00Z'
                    if iso_str.endswith('Z'):
                        return datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%SZ")
                    return datetime.fromisoformat(iso_str)
                except Exception:
                    try:
                        # Fallback to date only
                        return datetime.strptime(iso_str.split('T')[0], "%Y-%m-%d")
                    except Exception:
                        return None

            # Enrich each package with upstream info and libyear where possible
            for package in packages:
                package["collector_name"] = collector_name
                if distribution_version:
                    package["distribution_version"] = distribution_version

                # Skip if upstream already present
                if not package.get("upstream_version"):
                    # Try GitHub detection from source_url
                    source = package.get("source_url") or package.get("website") or ""
                    m = re.search(r"github\.com/([^/]+/[^/]+)", source)
                    if m:
                        repo = m.group(1).rstrip(".git")
                        try:
                            latest = gh_detector.get_latest_version(repo)
                            if latest:
                                package["upstream_version"] = latest
                                date_iso = gh_detector.get_release_date(repo, latest)
                                upstream_dt = parse_iso_to_datetime(date_iso)
                                if upstream_dt:
                                    package["upstream_release_date"] = upstream_dt.date()
                            # Try to get language
                            try:
                                lang = gh_detector.get_repo_language(repo)
                                if lang:
                                    package["language"] = lang
                            except Exception:
                                pass
                        except Exception:
                            pass

                # Try PyPI detection if still empty (use package_name)
                if not package.get("upstream_version"):
                    pkgname = package.get("package_name")
                    if pkgname:
                        try:
                            latest = pypi_detector.get_latest_version(pkgname)
                            if latest:
                                package["upstream_version"] = latest
                                date_iso = pypi_detector.get_release_date(pkgname, latest)
                                upstream_dt = parse_iso_to_datetime(date_iso)
                                if upstream_dt:
                                    package["upstream_release_date"] = upstream_dt.date()
                                # mark language as Python if PyPI matched
                                package.setdefault("language", "Python")
                        except Exception:
                            pass

                # Calculate libyear using available dates or versions
                try:
                    current_ver = package.get("version", "")
                    upstream_ver = package.get("upstream_version", current_ver)
                    current_date = package.get("system_release_date")
                    upstream_date = package.get("upstream_release_date")

                    # Convert dates to datetime for libyear calculator
                    cur_dt = None
                    up_dt = None
                    if isinstance(current_date, datetime):
                        cur_dt = current_date
                    elif current_date:
                        try:
                            cur_dt = datetime.strptime(str(current_date), "%Y-%m-%d")
                        except Exception:
                            cur_dt = None

                    if isinstance(upstream_date, datetime):
                        up_dt = upstream_date
                    elif upstream_date:
                        try:
                            up_dt = datetime.strptime(str(upstream_date), "%Y-%m-%d")
                        except Exception:
                            up_dt = None

                    libyear = ly_calc.calculate_libyear(current_ver, upstream_ver, cur_dt, up_dt)
                    package["libyear"] = round(libyear, 3)
                    package["days_outdated"] = int(libyear * 365)
                    package["is_outdated"] = libyear > 0.0
                except Exception:
                    package["libyear"] = None
                    package["days_outdated"] = None
                    package["is_outdated"] = False

            saved_count = db_manager.save_packages_batch(packages, repository_id)
            self.logger.info(f"Saved {saved_count}/{len(packages)} packages to database")
            return saved_count
        except Exception as e:
            self.logger.error(f"Error saving to database: {e}")
            return 0

