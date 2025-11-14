"""
Database connection management for MariaDB/MySQL.
"""

from typing import Optional, Dict, Any
import logging
import pymysql
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """Manage database connections to MariaDB/MySQL."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize database connection.

        Args:
            config: Database configuration dictionary containing:
                - host: Database host
                - port: Database port (default: 3306)
                - user: Database user
                - password: Database password
                - database: Database name
                - charset: Character set (default: utf8mb4)
        """
        self.config = config
        self.host = config.get("host", "localhost")
        self.port = config.get("port", 3306)
        self.user = config.get("user")
        self.password = config.get("password")
        self.database = config.get("database")
        self.charset = config.get("charset", "utf8mb4")
        self.logger = logging.getLogger(self.__class__.__name__)

    def get_connection(self) -> pymysql.Connection:
        """
        Get a database connection.

        Returns:
            PyMySQL connection object

        Raises:
            pymysql.Error: If connection fails
        """
        try:
            connection = pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                charset=self.charset,
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False
            )
            return connection
        except pymysql.Error as e:
            self.logger.error(f"Error connecting to database: {e}")
            raise

    @contextmanager
    def get_cursor(self):
        """
        Get a database cursor as context manager.

        Yields:
            Database cursor

        Example:
            with db.get_cursor() as cursor:
                cursor.execute("SELECT * FROM packages")
        """
        connection = None
        cursor = None
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            yield cursor
            connection.commit()
        except Exception as e:
            if connection:
                connection.rollback()
            self.logger.error(f"Database error: {e}")
            raise
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()

    def test_connection(self) -> bool:
        """
        Test database connection.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT 1")
                return True
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False

    def execute_query(self, query: str, params: Optional[tuple] = None) -> list:
        """
        Execute a SELECT query and return results.

        Args:
            query: SQL query string
            params: Optional query parameters

        Returns:
            List of result dictionaries
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()
        except Exception as e:
            self.logger.error(f"Error executing query: {e}")
            return []

    def execute_update(self, query: str, params: Optional[tuple] = None) -> int:
        """
        Execute an INSERT/UPDATE/DELETE query.

        Args:
            query: SQL query string
            params: Optional query parameters

        Returns:
            Number of affected rows
        """
        try:
            with self.get_cursor() as cursor:
                affected_rows = cursor.execute(query, params)
                return affected_rows
        except Exception as e:
            self.logger.error(f"Error executing update: {e}")
            return 0

