# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
