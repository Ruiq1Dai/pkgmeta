#!/usr/bin/env python3
"""
Database migration script for initializing and updating database schema.
"""

import argparse
import logging
import sys
import yaml
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pkgharvest.database import DatabaseConnection, DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


def load_database_config(config_path: str) -> dict:
    """
    Load database configuration from YAML file.

    Args:
        config_path: Path to configuration file

    Returns:
        Database configuration dictionary
    """
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
            return config.get("database", {})
    except Exception as e:
        logger.error(f"Error loading database config: {e}")
        return {}


def create_database(db_config: dict) -> bool:
    """
    Create database if it doesn't exist.

    Args:
        db_config: Database configuration dictionary

    Returns:
        True if successful, False otherwise
    """
    try:
        import pymysql
        # Connect without specifying database
        temp_config = db_config.copy()
        database_name = temp_config.pop("database")
        
        connection = pymysql.connect(
            host=temp_config.get("host", "localhost"),
            port=temp_config.get("port", 3306),
            user=temp_config.get("user"),
            password=temp_config.get("password"),
            charset=temp_config.get("charset", "utf8mb4")
        )
        
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {database_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            logger.info(f"Database '{database_name}' created or already exists")
        
        connection.close()
        return True
    except Exception as e:
        logger.error(f"Error creating database: {e}")
        return False


def initialize_schema(db_config: dict) -> bool:
    """
    Initialize database schema.

    Args:
        db_config: Database configuration dictionary

    Returns:
        True if successful, False otherwise
    """
    try:
        db_connection = DatabaseConnection(db_config)
        
        # Test connection
        if not db_connection.test_connection():
            logger.error("Failed to connect to database")
            return False
        
        db_manager = DatabaseManager(db_connection)
        
        if db_manager.initialize_schema():
            logger.info("Database schema initialized successfully")
            return True
        else:
            logger.error("Failed to initialize database schema")
            return False
    except Exception as e:
        logger.error(f"Error initializing schema: {e}")
        return False


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Database migration script")
    parser.add_argument(
        "--config",
        type=str,
        default="configs/database.yml",
        help="Path to database configuration file"
    )
    parser.add_argument(
        "--create-db",
        action="store_true",
        help="Create database if it doesn't exist"
    )
    parser.add_argument(
        "--init-schema",
        action="store_true",
        help="Initialize database schema"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run all migration steps"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load configuration
    db_config = load_database_config(args.config)
    if not db_config:
        logger.error("Failed to load database configuration")
        sys.exit(1)

    success = True

    # Create database
    if args.create_db or args.all:
        logger.info("Creating database...")
        import pymysql
        if not create_database(db_config):
            success = False

    # Initialize schema
    if args.init_schema or args.all:
        logger.info("Initializing database schema...")
        if not initialize_schema(db_config):
            success = False

    if not args.create_db and not args.init_schema and not args.all:
        logger.warning("No action specified. Use --create-db, --init-schema, or --all")
        parser.print_help()
        sys.exit(1)

    if success:
        logger.info("Migration completed successfully")
    else:
        logger.error("Migration completed with errors")
        sys.exit(1)


if __name__ == "__main__":
    main()

