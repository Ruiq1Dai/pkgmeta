## OpenHarmony 最小产物模式（基础使用）

### 功能
- 获取并解析 OpenHarmony 数据，按 Fedora 契约生成两份产物（结构与字段顺序完全一致）：
  - generated/openharmony_all_packages.json
  - generated/openharmony_release_repodata.xml

### 环境
- Python 3.8+
- 依赖：requests、bs4、zstandard（建议）

```bash
pip install requests bs4 zstandard
```

可选：设置 GitCode 令牌提升稳定性

```bash
set GITCODE_TOKEN=your_token   # Windows
export GITCODE_TOKEN=your_token # Linux/macOS
```

### 运行
在 demo 目录下执行：

```bash
python start.py openharmony
```

完成后仅在 generated/ 目录生成以上两份文件（中间文件会清理）。

### 说明
- JSON 契约参考：demo/generated/fedora_41/fedora_41_all_packages.json
- XML 契约参考：demo/generated/fedora_41/fedora_41_release_repodata.xml
- 仅包含基础流程：Fetcher 获取 → Parser 解析 → 按契约输出两份最小产物。
