# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `tests/test_orchestrator.py` — 9 个 Orchestrator 集成测试，覆盖 `fetch_all` 跨分类去重、重复抓取更新路径、详情抓取失败容错、`recommend` 排序与持久化、`stats`/`history` 聚合，以及月份窗口边界回归（不依赖网络，使用 `tmp_path` + `MagicMock` 替换 `DoubanBookSource`）

### Fixed

- `BookFilter.filter()` 日期窗口用 `relativedelta` 做精确月份回退，替代原先 `timedelta(days=30*months)` 的近似算法（修复 `test_combined_filter` 边界用例失败）
- `Orchestrator._load_books_from_store` 同样改用 `relativedelta`（同款 bug：`recommend` 在跨月边界会错误过滤掉近 3 月内出版的书）

### Changed

- `pyproject.toml` / `README.md` / `README.zh-CN.md` / `CONTRIBUTING.md` 中的仓库占位符替换为实际地址 `huisystems/bookrec`
- 显式声明 `python-dateutil>=2.8.0` 依赖

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
