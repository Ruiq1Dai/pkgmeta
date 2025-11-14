"""
OpenEuler package collector.
"""

from typing import Dict, List, Optional, Any
import logging
import requests
import gzip
import xml.etree.ElementTree as ET
from io import BytesIO

from pkgharvest.core.base_collector import BaseCollector

logger = logging.getLogger(__name__)


class OpenEulerCollector(BaseCollector):
    """Collector for OpenEuler RPM packages."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize OpenEuler collector.

        Args:
            config: Configuration dictionary from collectors.yml
        """
        super().__init__(config)
        self.base_url = self.config.get("base_url", "https://repo.openeuler.org")
        self.family = self.config.get("family", "centos")
        self.versions = self.config.get("versions", [])
        self.package_links = self.config.get("package_links", {})

    def get_repository_url(self, version: Optional[str] = None) -> str:
        """
        Get the repository URL for OpenEuler.

        Args:
            version: OpenEuler version (e.g., "22.03-LTS", "24.03-LTS")

        Returns:
            Repository URL string
        """
        version_config = self._get_version_config(version)
        if version_config:
            return version_config.get("metadata_url", f"{self.base_url}/openEuler-{version}/")
        return self.base_url

    def _get_version_config(self, version: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific version.

        Args:
            version: Version identifier

        Returns:
            Version configuration dictionary or None
        """
        if not version:
            return None

        for ver_config in self.versions:
            if ver_config.get("version") == version:
                return ver_config
        return None

    def collect_packages(self, version: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Collect package information from OpenEuler repository.

        Args:
            version: OpenEuler version identifier (e.g., "22.03-LTS-SP3", "24.03-LTS")

        Returns:
            List of package dictionaries
        """
        self.logger.info(f"Collecting packages from OpenEuler {version or 'latest'}")
        packages = []

        try:
            version_config = self._get_version_config(version)
            if not version_config:
                self.logger.error(f"Version {version} not found in configuration")
                return packages

            metadata_url = version_config.get("metadata_url", "")
            if not metadata_url:
                self.logger.error(f"No metadata URL for OpenEuler {version}")
                return packages

            self.logger.info(f"Fetching packages from {metadata_url}")
            packages = self._fetch_repodata(metadata_url, version)

        except Exception as e:
            self.logger.error(f"Error collecting packages: {e}", exc_info=True)

        self.logger.info(f"Collected {len(packages)} packages from OpenEuler {version}")
        return packages

    def _fetch_repodata(self, metadata_url: str, version: str) -> List[Dict[str, Any]]:
        """
        Fetch and parse repodata from repository.

        Args:
            metadata_url: URL to repository metadata
            version: OpenEuler version

        Returns:
            List of package dictionaries
        """
        packages = []

        try:
            # Fetch repomd.xml to get primary.xml.gz location
            repomd_url = f"{metadata_url.rstrip('/')}/repodata/repomd.xml"
            self.logger.debug(f"Fetching repomd.xml from {repomd_url}")

            response = requests.get(repomd_url, timeout=30)
            response.raise_for_status()

            # Parse repomd.xml to find primary.xml.gz
            primary_location = self._parse_repomd(response.content)
            if not primary_location:
                self.logger.error("Could not find primary.xml.gz location in repomd.xml")
                return packages

            # Fetch primary.xml.gz
            primary_url = f"{metadata_url.rstrip('/')}/{primary_location}"
            self.logger.debug(f"Fetching primary metadata from {primary_url}")

            response = requests.get(primary_url, timeout=60)
            response.raise_for_status()

            # Decompress and parse
            with gzip.GzipFile(fileobj=BytesIO(response.content)) as f:
                xml_content = f.read()

            packages = self._parse_rpm_metadata(xml_content, version)

        except requests.RequestException as e:
            self.logger.error(f"HTTP error fetching repodata: {e}")
        except Exception as e:
            self.logger.error(f"Error processing repodata: {e}", exc_info=True)

        return packages

    def _parse_repomd(self, repomd_content: bytes) -> Optional[str]:
        """
        Parse repomd.xml to find primary.xml.gz location.

        Args:
            repomd_content: Raw repomd.xml content

        Returns:
            Relative path to primary.xml.gz or None
        """
        try:
            root = ET.fromstring(repomd_content)
            # Namespace handling
            ns = {'repo': 'http://linux.duke.edu/metadata/repo'}

            for data in root.findall('repo:data', ns):
                if data.get('type') == 'primary':
                    location = data.find('repo:location', ns)
                    if location is not None:
                        return location.get('href')

            # Fallback without namespace
            for data in root.findall('data'):
                if data.get('type') == 'primary':
                    location = data.find('location')
                    if location is not None:
                        return location.get('href')

        except Exception as e:
            self.logger.error(f"Error parsing repomd.xml: {e}")

        return None

    def _parse_rpm_metadata(self, xml_content: bytes, version: str) -> List[Dict[str, Any]]:
        """
        Parse RPM repository metadata (primary.xml).

        Args:
            xml_content: Raw XML content from primary.xml
            version: OpenEuler version

        Returns:
            List of package dictionaries
        """
        packages = []

        try:
            root = ET.fromstring(xml_content)
            ns = {'rpm': 'http://linux.duke.edu/metadata/common'}

            for package_elem in root.findall('rpm:package', ns):
                if package_elem.get('type') != 'rpm':
                    continue

                try:
                    # Extract basic package info
                    name_elem = package_elem.find('rpm:name', ns)
                    arch_elem = package_elem.find('rpm:arch', ns)

                    # Skip non-source packages
                    if arch_elem is not None and arch_elem.text != 'src':
                        continue

                    version_elem = package_elem.find('rpm:version', ns)
                    summary_elem = package_elem.find('rpm:summary', ns)
                    description_elem = package_elem.find('rpm:description', ns)
                    url_elem = package_elem.find('rpm:url', ns)
                    packager_elem = package_elem.find('rpm:packager', ns)
                    time_elem = package_elem.find('rpm:time', ns)

                    package_name = name_elem.text if name_elem is not None else ""
                    if not package_name:
                        continue

                    pkg_version = version_elem.get('ver') if version_elem is not None else ""
                    pkg_release = version_elem.get('rel') if version_elem is not None else ""

                    # Build full version string
                    full_version = pkg_version
                    if pkg_release:
                        full_version = f"{pkg_version}-{pkg_release}"

                    # Get build time
                    build_time = None
                    if time_elem is not None:
                        build_timestamp = time_elem.get('build')
                        if build_timestamp:
                            from datetime import datetime
                            build_time = datetime.fromtimestamp(int(build_timestamp)).date()

                    # Construct package data matching database schema
                    package_data = {
                        "package_name": package_name,
                        "display_name": package_name,
                        "version": full_version,
                        "description": description_elem.text if description_elem is not None else "",
                        "website": url_elem.text if url_elem is not None else "",
                        "source_url": self._build_source_url(package_name, version),
                        "system_release_date": build_time,
                        # Fields to be filled by detectors
                        "upstream_version": None,
                        "upstream_release_date": None,
                        "libyear": None,
                        "days_outdated": None,
                        "language": None,
                        "is_outdated": False,
                        # Metadata
                        "_openeuler_version": version,
                    }

                    packages.append(package_data)

                except Exception as e:
                    self.logger.warning(f"Error parsing package element: {e}")
                    continue

            # Fallback without namespace
            if not packages:
                for package_elem in root.findall('package'):
                    if package_elem.get('type') != 'rpm':
                        continue

                    try:
                        name_elem = package_elem.find('name')
                        arch_elem = package_elem.find('arch')

                        if arch_elem is not None and arch_elem.text != 'src':
                            continue

                        version_elem = package_elem.find('version')
                        summary_elem = package_elem.find('summary')
                        description_elem = package_elem.find('description')
                        url_elem = package_elem.find('url')
                        time_elem = package_elem.find('time')

                        package_name = name_elem.text if name_elem is not None else ""
                        if not package_name:
                            continue

                        pkg_version = version_elem.get('ver') if version_elem is not None else ""
                        pkg_release = version_elem.get('rel') if version_elem is not None else ""

                        full_version = pkg_version
                        if pkg_release:
                            full_version = f"{pkg_version}-{pkg_release}"

                        build_time = None
                        if time_elem is not None:
                            build_timestamp = time_elem.get('build')
                            if build_timestamp:
                                from datetime import datetime
                                build_time = datetime.fromtimestamp(int(build_timestamp)).date()

                        package_data = {
                            "package_name": package_name,
                            "display_name": package_name,
                            "version": full_version,
                            "description": description_elem.text if description_elem is not None else "",
                            "website": url_elem.text if url_elem is not None else "",
                            "source_url": self._build_source_url(package_name, version),
                            "system_release_date": build_time,
                            "upstream_version": None,
                            "upstream_release_date": None,
                            "libyear": None,
                            "days_outdated": None,
                            "language": None,
                            "is_outdated": False,
                            "_openeuler_version": version,
                        }

                        packages.append(package_data)

                    except Exception as e:
                        self.logger.warning(f"Error parsing package element: {e}")
                        continue

        except Exception as e:
            self.logger.error(f"Error parsing RPM metadata XML: {e}", exc_info=True)

        return packages

    def _build_source_url(self, package_name: str, version: str) -> str:
        """
        Build source URL for a package.

        Args:
            package_name: Package name
            version: OpenEuler version

        Returns:
            Source URL string
        """
        sources_template = self.package_links.get("sources_template", "")
        if not sources_template:
            return ""

        return sources_template.format(srcname=package_name, version=version)

    def get_package_info(self, package_name: str) -> Optional[Dict[str, Any]]:
        """
        Get information for a specific package.

        Args:
            package_name: Name of the package

        Returns:
            Dictionary containing package information or None if not found
        """
        self.logger.info(f"Fetching package info for {package_name}")
        try:
            # TODO: Implement single package info retrieval if needed
            return None
        except Exception as e:
            self.logger.error(f"Error fetching package info: {e}")
            return None
