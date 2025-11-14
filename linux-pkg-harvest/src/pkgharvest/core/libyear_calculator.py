"""
LibYear calculator for measuring dependency freshness.
"""

from typing import Dict, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class LibYearCalculator:
    """Calculate LibYear metric for packages and dependencies."""

    def __init__(self):
        """Initialize the LibYear calculator."""
        self.logger = logging.getLogger(self.__class__.__name__)

    def calculate_libyear(
        self,
        current_version: str,
        latest_version: str,
        release_date_current: Optional[datetime] = None,
        release_date_latest: Optional[datetime] = None
    ) -> float:
        """
        Calculate LibYear between two versions.

        Args:
            current_version: Current version string
            latest_version: Latest version string
            release_date_current: Release date of current version
            release_date_latest: Release date of latest version

        Returns:
            LibYear value as float
        """
        if release_date_current and release_date_latest:
            # Calculate based on actual release dates
            delta = release_date_latest - release_date_current
            return delta.days / 365.25
        else:
            # Fallback: estimate based on version numbers
            # This is a simplified calculation
            try:
                from packaging import version
                v_current = version.parse(current_version)
                v_latest = version.parse(latest_version)

                if v_current >= v_latest:
                    return 0.0

                # Simple heuristic: assume 0.1 years per minor version difference
                # This is not accurate but provides a rough estimate
                major_diff = v_latest.major - v_current.major
                minor_diff = v_latest.minor - v_current.minor
                patch_diff = getattr(v_latest, 'micro', 0) - getattr(v_current, 'micro', 0)

                estimated_years = (major_diff * 1.0) + (minor_diff * 0.1) + (patch_diff * 0.01)
                return max(0.0, estimated_years)
            except Exception as e:
                self.logger.warning(f"Error calculating LibYear: {e}")
                return 0.0

    def calculate_package_libyear(
        self,
        package_info: Dict,
        latest_version_info: Optional[Dict] = None
    ) -> Dict[str, float]:
        """
        Calculate LibYear metrics for a package.

        Args:
            package_info: Current package information dictionary
            latest_version_info: Latest version information dictionary

        Returns:
            Dictionary containing LibYear metrics
        """
        current_version = package_info.get("version", "")
        latest_version = latest_version_info.get("version", "") if latest_version_info else current_version

        libyear = self.calculate_libyear(
            current_version,
            latest_version,
            package_info.get("release_date"),
            latest_version_info.get("release_date") if latest_version_info else None
        )

        return {
            "libyear": libyear,
            "current_version": current_version,
            "latest_version": latest_version,
            "is_outdated": libyear > 0.0
        }

    def calculate_dependency_libyear(
        self,
        package_info: Dict,
        dependency_versions: Dict[str, Dict]
    ) -> Dict[str, Dict[str, float]]:
        """
        Calculate LibYear for all dependencies of a package.

        Args:
            package_info: Package information dictionary
            dependency_versions: Dictionary mapping dependency names to version info

        Returns:
            Dictionary mapping dependency names to LibYear metrics
        """
        results = {}
        dependencies = package_info.get("dependencies", [])

        for dep in dependencies:
            dep_name = dep.get("name") if isinstance(dep, dict) else str(dep)
            if dep_name in dependency_versions:
                dep_info = dependency_versions[dep_name]
                results[dep_name] = self.calculate_package_libyear(
                    {"version": dep.get("version", "") if isinstance(dep, dict) else ""},
                    dep_info
                )

        return results

