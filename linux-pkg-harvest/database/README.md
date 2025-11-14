# 数据库使用说明

本项目支持将采集的包数据存储到 MariaDB/MySQL 数据库中。

## 文件说明

- `schema.sql` - 数据库表结构定义 SQL 脚本
- `../configs/database.yaml` - 数据库连接配置文件
- `../scripts/migrate_db.py` - 数据库迁移和初始化脚本

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置数据库连接

编辑 `configs/database.yaml` 文件，设置数据库连接信息：

```yaml
database:
  host: "localhost"
  port: 3306
  user: "root"
  password: "your_password"
  database: "pkg_harvest"
  charset: "utf8mb4"
```

### 3. 初始化数据库

运行迁移脚本创建数据库和表结构：

```bash
# 创建数据库并初始化表结构
python scripts/migrate_db.py --all

# 或者分步执行
python scripts/migrate_db.py --create-db    # 仅创建数据库
python scripts/migrate_db.py --init-schema  # 仅初始化表结构
```

### 4. 使用数据库存储

#### 方式一：使用 run_collector.py

```bash
# 保存到数据库
python scripts/run_collector.py --collector ubuntu --version 22.04 --database

# 保存到文件（默认）
python scripts/run_collector.py --collector ubuntu --version 22.04 --output output.json
```

#### 方式二：使用 sync_all.py

```bash
# 同步所有采集器到数据库
python scripts/sync_all.py --database

# 同步到文件（默认）
python scripts/sync_all.py
```

## 数据库表结构

### repositories 表
存储仓库信息：
- `id` - 主键
- `name` - 仓库名称
- `url` - 仓库 URL
- `type` - 类型 (rpm/deb)
- `distribution` - 发行版名称
- `version` - 版本
- `arch` - 架构
- `enabled` - 是否启用

### packages 表
存储包信息：
- `id` - 主键
- `name` - 包名
- `version` - 版本
- `release` - 发布版本
- `arch` - 架构
- `description` - 描述
- `source_url` - 源码 URL
- `repository_id` - 关联的仓库 ID
- `collector_name` - 采集器名称
- `distribution_version` - 发行版版本
- `dependencies` - 依赖关系 (JSON 格式)
- `created_at` - 创建时间
- `updated_at` - 更新时间

### dependencies 表
存储依赖关系（可选，用于规范化存储）：
- `id` - 主键
- `package_id` - 包 ID
- `dependency_name` - 依赖包名
- `dependency_version` - 依赖版本
- `dependency_type` - 依赖类型 (runtime/build/test)

## 使用示例

### Python 代码中使用

```python
from pkgharvest.database import DatabaseConnection, DatabaseManager
from pkgharvest.core.data_processor import DataProcessor
import yaml

# 加载配置
with open("configs/database.yml") as f:
    config = yaml.safe_load(f)

# 创建数据库连接
db_connection = DatabaseConnection(config["database"])
db_manager = DatabaseManager(db_connection)

# 保存包数据
processor = DataProcessor()
packages = [...]  # 你的包数据列表
processor.save_to_database(
    packages,
    db_manager,
    collector_name="ubuntu",
    distribution_version="22.04"
)

# 查询包
packages = db_manager.search_packages(
    name_pattern="python",
    collector_name="ubuntu",
    limit=100
)
```
