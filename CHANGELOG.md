# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.2] - 2026-06-26

### Added

- `.github/workflows/publish.yml` — 自动发布到 PyPI / TestPyPI。使用 OIDC trusted publishing（无需 API token secret），触发条件：`v*` tag push 自动试发到 TestPyPI；`workflow_dispatch` 手动选 TestPyPI / PyPI 目标。Workflow 包含 build → tests → `twine check` → upload artifact → publish 的完整链路
- **Ruff lint 与 format 集成**：`pyproject.toml` 新增 `[tool.ruff]` 段，启用 `E/W/F/B/I/UP` 规则族，line-length 100，target Python 3.10。CI 的 `test` job 增 `ruff check .` 与 `ruff format --check .` 步骤（与 pytest 并行，只跑一次不重复 4 个 Python 版本）
- `tests/test_search_note.py` — 8 个直接覆盖 `Orchestrator.search` / `Orchestrator.add_note` 的集成测试（之前这两个方法只通过 store 层被 transitive 测过）：title 命中、author 命中、大小写不敏感、无命中返回空、跳过 `__索引.md`、首次添加笔记生成 `## 笔记` 节、重复 add_note 覆盖（不追加）、不存在 douban_id 抛 `ValueError`

### Changed

- 全仓库 ruff 自动修复了 97 个历史 lint 问题（PEP 604 注解、import 排序、unused import、f-string 占位符、文件末尾换行等），手修了 10 处 E501 过长行 + 1 处 B904（`raise ... from None`），并 `ruff format` 重整了 23 个文件的格式

### Fixed

- `pyproject.toml` 补上 `readme = "README.md"` 和 `license = { file = "LICENSE" }` 字段，消除 `twine check` 报的 `long_description` / `long_description_content_type` missing 警告，使包能直接 `pip install` 后正常显示 README

## [0.2.1] - 2026-06-26

### Added

- `tests/test_orchestrator.py` — 9 个 Orchestrator 集成测试，覆盖 `fetch_all` 跨分类去重、重复抓取更新路径、详情抓取失败容错、`recommend` 排序与持久化、`stats`/`history` 聚合，以及月份窗口边界回归（不依赖网络，使用 `tmp_path` + `MagicMock` 替换 `DoubanBookSource`）
- `tests/test_cli.py` — CLI 端到端测试，验证 `bookrec fetch` 在内部异常时返回非零退出码
- CI 矩阵覆盖 Python 3.10（与 `pyproject.toml` 的 `requires-python = ">=3.10"` 对齐）

### Fixed

- `BookFilter.filter()` 日期窗口用 `relativedelta` 做精确月份回退，替代原先 `timedelta(days=30*months)` 的近似算法（修复 `test_combined_filter` 边界用例失败）
- `Orchestrator._load_books_from_store` 同样改用 `relativedelta`（同款 bug：`recommend` 在跨月边界会错误过滤掉近 3 月内出版的书）
- `ObsidianStore.save_book` 漏写 `description` / `catalog` 到 YAML frontmatter，导致 `Orchestrator._dedup_and_store` 的"已有 description 就跳过详情抓取"判断不生效。现在 description/catalog 同时入 yaml 与 markdown body（增量最小的 schema 变更）

### Changed

- `pyproject.toml` / `README.md` / `README.zh-CN.md` / `CONTRIBUTING.md` 中的仓库占位符替换为实际地址 `huisystems/bookrec`
- 显式声明 `python-dateutil>=2.8.0` 依赖
- CI 缓存：`pip` 走 `actions/setup-python` 内置缓存，Playwright 浏览器走 `actions/cache`（cold run ~60-90s 节省）
- `bookrec fetch` 在内部异常时返回非零退出码（此前仅打印错误，CI 集成时拿不到失败信号）

### Removed

- 根目录临时脚本 `extract_top25.py` 及其输出的散落推荐 Markdown（功能由 `bookrec recommend --top 25 --output` 完全覆盖）

## [0.2.0] - 2026-05-09

### Added

- CLI with 8 commands: `fetch`, `recommend`, `list`, `search`, `note`, `stats`, `history`
- Obsidian-compatible knowledge base storage with YAML frontmatter and backlinks
- Douban tag page scraping for business (经管) and AI categories
- Bilingual book recommendation output (Chinese / English)
- Modular architecture with `src/cli/`, `src/core/`, `src/data_sources/`, `src/knowledge/`, `src/output/`, `src/services/`
- Service orchestrator for coordinated fetch → filter → store pipeline
- Configuration management module (`src/core/config.py`)
- Abstract base class for data sources (`src/data_sources/base.py`)
- Enhanced book model with additional fields

### Changed

- Full v2 refactoring: standalone script → modular package architecture
- Douban scraper redesigned for category-based tag page scraping
- Markdown output generator improved with richer formatting
- Book filtering service refactored for modularity

## [0.1.0] - 2026-05-07

### Added

- Initial release: basic Douban scraping + markdown output
- Project structure with `main.py`, `src/`, `tests/`
