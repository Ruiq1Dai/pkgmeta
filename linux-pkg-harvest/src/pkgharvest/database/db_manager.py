"""
Database manager for package data operations.
"""

from typing import List, Dict, Any, Optional
import logging
import json
from datetime import datetime, date
from .db_connection import DatabaseConnection
from .models import Repository, Package, SyncLog, RepositoryStats

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manage database operations for packages."""

    def __init__(self, db_connection: DatabaseConnection):
        """
        Initialize database manager.

        Args:
            db_connection: DatabaseConnection instance
        """
        self.db = db_connection
        self.logger = logging.getLogger(self.__class__.__name__)

    def initialize_schema(self) -> bool:
        """
        Initialize database schema (create tables).

        Returns:
            True if successful, False otherwise
        """
        try:
            schemas = [
                Repository.get_table_schema(),
                Package.get_table_schema(),
                SyncLog.get_table_schema(),
                RepositoryStats.get_table_schema(),
            ]

            with self.db.get_cursor() as cursor:
                for schema in schemas:
                    cursor.execute(schema)
                self.logger.info("Database schema initialized successfully")
                return True
        except Exception as e:
            self.logger.error(f"Error initializing schema: {e}")
            return False

    # ==================== Repository Operations ====================

    def save_repository(self, repo_data: Dict[str, Any]) -> Optional[int]:
        """
        Save a repository to database.

        Args:
            repo_data: Repository data dictionary

        Returns:
            Repository ID if successful, None otherwise
        """
        try:
            query = """
                INSERT INTO repository (
                    name, display_name, sync_enabled, last_sync_time, last_sync_status
                ) VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    display_name = VALUES(display_name),
                    sync_enabled = VALUES(sync_enabled),
                    last_sync_time = VALUES(last_sync_time),
                    last_sync_status = VALUES(last_sync_status),
                    updated_at = CURRENT_TIMESTAMP
            """

            params = (
                repo_data.get("name", ""),
                repo_data.get("display_name", ""),
                repo_data.get("sync_enabled", True),
                repo_data.get("last_sync_time"),
                repo_data.get("last_sync_status", "success"),
            )

            with self.db.get_cursor() as cursor:
                cursor.execute(query, params)
                repo_id = cursor.lastrowid

                if repo_id == 0:
                    cursor.execute("SELECT id FROM repository WHERE name = %s", (repo_data.get("name"),))
                    result = cursor.fetchone()
                    if result:
                        repo_id = result["id"]

                return repo_id
        except Exception as e:
            self.logger.error(f"Error saving repository: {e}")
            return None

    def get_repository(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a repository by name.

        Args:
            name: Repository name

        Returns:
            Repository data dictionary or None
        """
        try:
            query = "SELECT * FROM repository WHERE name = %s"
            results = self.db.execute_query(query, (name,))
            return results[0] if results else None
        except Exception as e:
            self.logger.error(f"Error getting repository: {e}")
            return None

    def get_repository_by_id(self, repo_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a repository by ID.

        Args:
            repo_id: Repository ID

        Returns:
            Repository data dictionary or None
        """
        try:
            query = "SELECT * FROM repository WHERE id = %s"
            results = self.db.execute_query(query, (repo_id,))
            return results[0] if results else None
        except Exception as e:
            self.logger.error(f"Error getting repository: {e}")
            return None


    def update_repository_sync_status(
        self,
        repo_id: int,
        status: str,
        sync_time: Optional[datetime] = None
    ) -> bool:
        """
        Update repository sync status.

        Args:
            repo_id: Repository ID
            status: Sync status ('success', 'failed', 'running')
            sync_time: Optional sync time

        Returns:
            True if successful, False otherwise
        """
        try:
            if sync_time:
                query = """
                    UPDATE repository 
                    SET last_sync_status = %s, last_sync_time = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """
                params = (status, sync_time, repo_id)
            else:
                query = """
                    UPDATE repository 
                    SET last_sync_status = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """
                params = (status, repo_id)

            affected = self.db.execute_update(query, params)
            return affected > 0
        except Exception as e:
            self.logger.error(f"Error updating repository sync status: {e}")
            return False

    # ==================== Package Operations ====================

    def save_package(self, package_data: Dict[str, Any], repository_id: int) -> Optional[int]:
        """
        Save a package to database.

        Args:
            package_data: Package data dictionary
            repository_id: Repository ID

        Returns:
            Package ID if successful, None otherwise
        """
        try:
            query = """
                INSERT INTO packages (
                    repository_id, package_name, display_name, version, upstream_version,
                    upstream_release_date, system_release_date, libyear, days_outdated,
                    source_url, language, website, description, is_outdated
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    display_name = VALUES(display_name),
                    upstream_version = VALUES(upstream_version),
                    upstream_release_date = VALUES(upstream_release_date),
                    system_release_date = VALUES(system_release_date),
                    libyear = VALUES(libyear),
                    days_outdated = VALUES(days_outdated),
                    source_url = VALUES(source_url),
                    language = VALUES(language),
                    website = VALUES(website),
                    description = VALUES(description),
                    is_outdated = VALUES(is_outdated),
                    last_updated = CURRENT_TIMESTAMP
            """

            params = (
                repository_id,
                package_data.get("package_name", ""),
                package_data.get("display_name"),
                package_data.get("version", ""),
                package_data.get("upstream_version"),
                package_data.get("upstream_release_date"),
                package_data.get("system_release_date"),
                package_data.get("libyear"),
                package_data.get("days_outdated"),
                package_data.get("source_url"),
                package_data.get("language"),
                package_data.get("website"),
                package_data.get("description"),
                package_data.get("is_outdated", False),
            )

            with self.db.get_cursor() as cursor:
                cursor.execute(query, params)
                package_id = cursor.lastrowid

                if package_id == 0:
                    cursor.execute(
                        "SELECT id FROM packages WHERE repository_id = %s AND package_name = %s AND version = %s",
                        (repository_id, package_data.get("package_name"), package_data.get("version"))
                    )
                    result = cursor.fetchone()
                    if result:
                        package_id = result["id"]

                return package_id
        except Exception as e:
            self.logger.error(f"Error saving package: {e}")
            return None

    def save_packages_batch(self, packages: List[Dict[str, Any]], repository_id: int, batch_size: int = 500) -> int:
        """
        Save multiple packages in batch using a single connection.

        Args:
            packages: List of package data dictionaries
            repository_id: Repository ID
            batch_size: Number of packages to insert per transaction (default: 500)

        Returns:
            Number of packages saved
        """
        saved_count = 0
        total_packages = len(packages)

        try:
            # Use a single connection for all operations
            with self.db.get_cursor() as cursor:
                # Process in batches to avoid long-running transactions
                for i in range(0, total_packages, batch_size):
                    batch = packages[i:i + batch_size]

                    for package in batch:
                        try:
                            query = """
                                INSERT INTO packages (
                                    repository_id, package_name, display_name, version, upstream_version,
                                    upstream_release_date, system_release_date, libyear, days_outdated,
                                    source_url, language, website, description, is_outdated
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON DUPLICATE KEY UPDATE
                                    display_name = VALUES(display_name),
                                    upstream_version = VALUES(upstream_version),
                                    upstream_release_date = VALUES(upstream_release_date),
                                    system_release_date = VALUES(system_release_date),
                                    libyear = VALUES(libyear),
                                    days_outdated = VALUES(days_outdated),
                                    source_url = VALUES(source_url),
                                    language = VALUES(language),
                                    website = VALUES(website),
                                    description = VALUES(description),
                                    is_outdated = VALUES(is_outdated),
                                    last_updated = CURRENT_TIMESTAMP
                            """

                            params = (
                                repository_id,
                                package.get("package_name", ""),
                                package.get("display_name"),
                                package.get("version", ""),
                                package.get("upstream_version"),
                                package.get("upstream_release_date"),
                                package.get("system_release_date"),
                                package.get("libyear"),
                                package.get("days_outdated"),
                                package.get("source_url"),
                                package.get("language"),
                                package.get("website"),
                                package.get("description"),
                                package.get("is_outdated", False),
                            )

                            cursor.execute(query, params)
                            saved_count += 1

                        except Exception as e:
                            self.logger.warning(f"Error saving package {package.get('package_name')}: {e}")
                            continue

                    # Log progress after each batch
                    self.logger.info(f"Saved {saved_count}/{total_packages} packages")

        except Exception as e:
            self.logger.error(f"Error in batch save: {e}")

        return saved_count

