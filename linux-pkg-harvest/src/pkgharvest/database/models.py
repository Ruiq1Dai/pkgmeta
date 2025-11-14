"""
Database models and table definitions.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, date
import json


class Repository:
    """Repository model for database operations."""

    def __init__(self, data: Dict[str, Any]):
        """
        Initialize repository from dictionary.

        Args:
            data: Repository data dictionary
        """
        self.id = data.get("id")
        self.name = data.get("name", "")
        self.display_name = data.get("display_name", "")
        self.sync_enabled = data.get("sync_enabled", True)
        self.last_sync_time = data.get("last_sync_time")
        self.last_sync_status = data.get("last_sync_status", "success")
        self.created_at = data.get("created_at")
        self.updated_at = data.get("updated_at")

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert repository to dictionary.

        Returns:
            Repository data as dictionary
        """
        return {
            "id": self.id,
            "name": self.name,
            "display_name": self.display_name,
            "sync_enabled": bool(self.sync_enabled) if self.sync_enabled is not None else True,
            "last_sync_time": self.last_sync_time.isoformat() if isinstance(self.last_sync_time, datetime) else self.last_sync_time,
            "last_sync_status": self.last_sync_status,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
            "updated_at": self.updated_at.isoformat() if isinstance(self.updated_at, datetime) else self.updated_at,
        }

    @staticmethod
    def get_table_schema() -> str:
        """
        Get SQL schema for repository table.

        Returns:
            SQL CREATE TABLE statement
        """
        return """
        CREATE TABLE IF NOT EXISTS repository (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL UNIQUE COMMENT '系统名称',
            display_name VARCHAR(200) NOT NULL COMMENT '显示名称',
            sync_enabled TINYINT(1) DEFAULT 1 COMMENT '是否启用同步',
            last_sync_time TIMESTAMP NULL COMMENT '最后同步时间',
            last_sync_status ENUM('success', 'failed', 'running') DEFAULT 'success' COMMENT '最后同步状态',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_sync_enabled (sync_enabled),
            INDEX idx_last_sync_status (last_sync_status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='系统表';
        """


class Package:
    """Package model for database operations."""

    def __init__(self, data: Dict[str, Any]):
        """
        Initialize package from dictionary.

        Args:
            data: Package data dictionary
        """
        self.id = data.get("id")
        self.repository_id = data.get("repository_id")
        self.package_name = data.get("package_name", "")
        self.display_name = data.get("display_name", "")
        self.version = data.get("version", "")
        self.upstream_version = data.get("upstream_version")
        self.upstream_release_date = data.get("upstream_release_date")
        self.system_release_date = data.get("system_release_date")
        self.libyear = data.get("libyear")
        self.days_outdated = data.get("days_outdated")
        self.source_url = data.get("source_url")
        self.language = data.get("language")
        self.website = data.get("website")
        self.description = data.get("description")
        self.is_outdated = data.get("is_outdated", False)
        self.last_updated = data.get("last_updated")
        self.created_at = data.get("created_at")

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert package to dictionary.

        Returns:
            Package data as dictionary
        """
        return {
            "id": self.id,
            "repository_id": self.repository_id,
            "package_name": self.package_name,
            "display_name": self.display_name,
            "version": self.version,
            "upstream_version": self.upstream_version,
            "upstream_release_date": self.upstream_release_date.isoformat() if isinstance(self.upstream_release_date, date) else self.upstream_release_date,
            "system_release_date": self.system_release_date.isoformat() if isinstance(self.system_release_date, date) else self.system_release_date,
            "libyear": float(self.libyear) if self.libyear is not None else None,
            "days_outdated": self.days_outdated,
            "source_url": self.source_url,
            "language": self.language,
            "website": self.website,
            "description": self.description,
            "is_outdated": bool(self.is_outdated) if self.is_outdated is not None else False,
            "last_updated": self.last_updated.isoformat() if isinstance(self.last_updated, datetime) else self.last_updated,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
        }

    @staticmethod
    def get_table_schema() -> str:
        """
        Get SQL schema for packages table.

        Returns:
            SQL CREATE TABLE statement
        """
        return """
        CREATE TABLE IF NOT EXISTS packages (
            id INT AUTO_INCREMENT PRIMARY KEY,
            repository_id INT NOT NULL COMMENT '系统ID',
            package_name VARCHAR(200) NOT NULL COMMENT '包名',
            display_name VARCHAR(300) COMMENT '显示名称',
            version VARCHAR(100) NOT NULL COMMENT '系统中当前版本',
            upstream_version VARCHAR(100) COMMENT '上游版本',
            upstream_release_date DATE COMMENT '上游发布日期',
            system_release_date DATE COMMENT '系统发布日期',
            libyear DECIMAL(6,3) COMMENT 'Libyear值',
            days_outdated INT COMMENT '过期天数',
            source_url TEXT COMMENT '源码地址',
            language VARCHAR(50) COMMENT '主要语言',
            website TEXT COMMENT '官网地址',
            description TEXT COMMENT '包描述',
            is_outdated TINYINT(1) DEFAULT 0 COMMENT '是否过期',
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_repository_id (repository_id),
            INDEX idx_package_name (package_name),   
            FOREIGN KEY (repository_id) REFERENCES repository(id) ON DELETE CASCADE,
            UNIQUE KEY unique_package (repository_id, package_name, version)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='软件包表';
        """


class SyncLog:
    """Sync log model for database operations."""

    def __init__(self, data: Dict[str, Any]):
        """
        Initialize sync log from dictionary.

        Args:
            data: Sync log data dictionary
        """
        self.id = data.get("id")
        self.repository_id = data.get("repository_id")
        self.sync_type = data.get("sync_type", "full")
        self.start_time = data.get("start_time")
        self.end_time = data.get("end_time")
        self.packages_total = data.get("packages_total", 0)
        self.packages_updated = data.get("packages_updated", 0)
        self.packages_added = data.get("packages_added", 0)
        self.packages_removed = data.get("packages_removed", 0)
        self.status = data.get("status", "running")
        self.error_message = data.get("error_message")
        self.logs = data.get("logs")
        self.created_at = data.get("created_at")

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert sync log to dictionary.

        Returns:
            Sync log data as dictionary
        """
        return {
            "id": self.id,
            "repository_id": self.repository_id,
            "sync_type": self.sync_type,
            "start_time": self.start_time.isoformat() if isinstance(self.start_time, datetime) else self.start_time,
            "end_time": self.end_time.isoformat() if isinstance(self.end_time, datetime) else self.end_time,
            "packages_total": self.packages_total,
            "packages_updated": self.packages_updated,
            "packages_added": self.packages_added,
            "packages_removed": self.packages_removed,
            "status": self.status,
            "error_message": self.error_message,
            "logs": self.logs,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
        }

    @staticmethod
    def get_table_schema() -> str:
        """
        Get SQL schema for sync_logs table.

        Returns:
            SQL CREATE TABLE statement
        """
        return """
        CREATE TABLE IF NOT EXISTS sync_logs (
            id INT AUTO_INCREMENT PRIMARY KEY,
            repository_id INT NOT NULL COMMENT '仓库ID',
            sync_type ENUM('full', 'incremental') NOT NULL COMMENT '同步类型',
            start_time TIMESTAMP NULL COMMENT '开始时间',
            end_time TIMESTAMP NULL COMMENT '结束时间',
            packages_total INT DEFAULT 0 COMMENT '总包数',
            packages_updated INT DEFAULT 0 COMMENT '更新包数',
            packages_added INT DEFAULT 0 COMMENT '新增包数',
            packages_removed INT DEFAULT 0 COMMENT '删除包数',
            status ENUM('running', 'success', 'failed', 'cancelled') DEFAULT 'running' COMMENT '状态',
            error_message TEXT COMMENT '错误信息',
            logs TEXT COMMENT '详细日志',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_repository_id (repository_id),
            INDEX idx_status (status),
            INDEX idx_sync_type (sync_type),
            INDEX idx_start_time (start_time),
            FOREIGN KEY (repository_id) REFERENCES repository(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='同步日志表';
        """


class RepositoryStats:
    """Repository statistics model for database operations."""

    def __init__(self, data: Dict[str, Any]):
        """
        Initialize repository stats from dictionary.

        Args:
            data: Repository stats data dictionary
        """
        self.id = data.get("id")
        self.repository_id = data.get("repository_id")
        self.stat_date = data.get("stat_date")
        self.total_packages = data.get("total_packages", 0)
        self.outdated_packages = data.get("outdated_packages", 0)
        self.avg_libyear = data.get("avg_libyear")
        self.max_libyear = data.get("max_libyear")
        self.median_libyear = data.get("median_libyear")
        self.language_stats = data.get("language_stats")
        self.created_at = data.get("created_at")

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert repository stats to dictionary.

        Returns:
            Repository stats data as dictionary
        """
        return {
            "id": self.id,
            "repository_id": self.repository_id,
            "stat_date": self.stat_date.isoformat() if isinstance(self.stat_date, date) else self.stat_date,
            "total_packages": self.total_packages,
            "outdated_packages": self.outdated_packages,
            "avg_libyear": float(self.avg_libyear) if self.avg_libyear is not None else None,
            "max_libyear": float(self.max_libyear) if self.max_libyear is not None else None,
            "median_libyear": float(self.median_libyear) if self.median_libyear is not None else None,
            "language_stats": self.language_stats if isinstance(self.language_stats, dict) else json.loads(self.language_stats) if isinstance(self.language_stats, str) else None,
            "created_at": self.created_at.isoformat() if isinstance(self.created_at, datetime) else self.created_at,
        }

    @staticmethod
    def get_table_schema() -> str:
        """
        Get SQL schema for repository_stats table.

        Returns:
            SQL CREATE TABLE statement
        """
        return """
        CREATE TABLE IF NOT EXISTS repository_stats (
            id INT AUTO_INCREMENT PRIMARY KEY,
            repository_id INT NOT NULL COMMENT '仓库ID',
            stat_date DATE NOT NULL COMMENT '统计日期',
            total_packages INT DEFAULT 0 COMMENT '总包数',
            outdated_packages INT DEFAULT 0 COMMENT '过期包数',
            avg_libyear DECIMAL(6,3) DEFAULT 0 COMMENT '平均libyear',
            max_libyear DECIMAL(6,3) DEFAULT 0 COMMENT '最大libyear',
            median_libyear DECIMAL(6,3) DEFAULT 0 COMMENT '中位数libyear',
            language_stats JSON COMMENT '语言统计',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_repository_id (repository_id),
            INDEX idx_stat_date (stat_date),
            UNIQUE KEY unique_stat (repository_id, stat_date),
            FOREIGN KEY (repository_id) REFERENCES repository(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='系统统计表';
        """
