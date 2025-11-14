-- Database schema for linux-pkg-harvest
-- MariaDB/MySQL compatible

-- Create database (run this manually if needed)
-- CREATE DATABASE IF NOT EXISTS pkg_harvest CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
-- USE pkg_harvest;

-- Repository table (系统表)
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

-- Packages table (软件包表)
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
    INDEX idx_version (version),
    INDEX idx_is_outdated (is_outdated),
    INDEX idx_language (language),
    INDEX idx_libyear (libyear),
    FOREIGN KEY (repository_id) REFERENCES repository(id) ON DELETE CASCADE,
    UNIQUE KEY unique_package (repository_id, package_name, version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='软件包表';

-- Sync logs table (同步日志表)
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

-- Repository stats table (系统统计表)
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
