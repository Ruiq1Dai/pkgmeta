#!/usr/bin/env python3
"""
Script to run a specific collector.
"""

import argparse
import logging
import sys
import yaml
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pkgharvest.collectors import (
    OpenEulerCollector,
    FedoraCollector,
)
from pkgharvest.core.data_processor import DataProcessor
from pkgharvest.database import DatabaseConnection, DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Collector mapping
COLLECTORS = {
    "openeuler": OpenEulerCollector,
    "fedora": FedoraCollector,
}


def load_config(config_path: str) -> dict:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to configuration file

    Returns:
        Configuration dictionary
    """
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return {}


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Run a specific package collector")
    parser.add_argument("collector", choices=COLLECTORS.keys(), help="Collector name")
    parser.add_argument("--version", required=True, help="Distribution version")
    parser.add_argument("--config", default="../configs/collectors.yml", help="Collector config path")
    parser.add_argument("--db-config", default="../configs/database.yml", help="Database config path")

    args = parser.parse_args()

    try:
        # Load configurations
        collector_config = load_config(args.config)
        db_config = load_config(args.db_config)

        if not collector_config or not db_config:
            logger.error("Failed to load configuration files")
            sys.exit(1)

        # Get collector-specific config
        collector_name = args.collector
        collector_conf = collector_config.get("collectors", {}).get(collector_name, {})

        if not collector_conf:
            logger.error(f"No configuration found for collector: {collector_name}")
            sys.exit(1)

        # Initialize database
        db_connection = DatabaseConnection(db_config.get("database", {}))
        db_manager = DatabaseManager(db_connection)

        # Get or create repository record
        repo_display_name = f"{collector_name.capitalize()} {args.version}"
        repo_name = f"{collector_name}_{args.version.replace('.', '_').replace('-', '_')}"

        repo_data = {
            "name": repo_name,
            "display_name": repo_display_name,
            "sync_enabled": True,
            "last_sync_status": "running",
        }

        repository_id = db_manager.save_repository(repo_data)
        if not repository_id:
            logger.error("Failed to create/get repository record")
            sys.exit(1)

        logger.info(f"Repository ID: {repository_id}")

        # Initialize collector
        collector_class = COLLECTORS[collector_name]
        collector = collector_class(collector_conf)

        # Collect packages
        logger.info(f"Starting collection for {collector_name} {args.version}")
        start_time = datetime.now()

        packages = collector.collect_packages(version=args.version)

        if not packages:
            logger.warning("No packages collected")
            db_manager.update_repository_sync_status(repository_id, "failed", start_time)
            sys.exit(0)

        logger.info(f"Collected {len(packages)} packages")

        # Save to database
        data_processor = DataProcessor()
        saved_count = data_processor.save_to_database(
            packages=packages,
            db_manager=db_manager,
            collector_name=collector_name,
            distribution_version=args.version,
            repository_id=repository_id
        )

        end_time = datetime.now()

        # Update repository sync status
        db_manager.update_repository_sync_status(
            repository_id,
            "success" if saved_count > 0 else "failed",
            end_time
        )

        logger.info(f"Successfully saved {saved_count}/{len(packages)} packages")
        logger.info(f"Collection completed in {(end_time - start_time).total_seconds():.2f} seconds")

    except Exception as e:
        logger.error(f"Error during collection: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
