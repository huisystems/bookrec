# bookrec

Automated book recommendation tool that scrapes Douban (豆瓣) for high-quality business and AI books, filters and ranks them, and builds a browsable Obsidian knowledge base.

---

## Features

- **Douban scraping** — Crawls Douban's latest and tag pages for business (经管) and AI books, with automatic deduplication across categories
- **Smart filtering and ranking** — Filters by rating, rating count, and publication date; ranks using a weighted score combining rating, popularity, and recency
- **Obsidian knowledge base** — Each book saved as a standalone Markdown file with YAML frontmatter, organized by category under a vault directory; includes auto-generated index and statistics
- **Bilingual CLI** — Click-based command-line interface with Chinese descriptions and English-compatible flag names; Rich-powered formatted table output
- **Full-text search** — Search across book titles, authors, and descriptions
- **Recommendation export** — Generate ranked recommendation lists as Markdown files or JSON
- **Annotation support** — Add personal notes to any book in the vault

---

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt
playwright install chromium

# 2. One-time login to Douban (saves cookie for scraping)
#    See "Authentication" below for details
bookrec login

# 3. Scrape latest books from Douban
bookrec fetch

# 4. Generate a ranked recommendation list
bookrec recommend --top 10 --output 推荐.md

# 5. Browse the vault
bookrec list-books
bookrec stats
```

Example `bookrec stats` output on a populated vault:

```
📊 知识库统计

  图书总数: 60 本

  分类分布:
    AI     | ███████████████████████ 23
    经管     | █████████████████████████████████████ 37
```

Example `bookrec recommend --top 3`:

```
1. 《段永平投资问答录（投资逻辑篇）》
   作者：段永平、雪球用户 · 评分 8.9 ⭐⭐⭐⭐½ (2134 人评价) · 推荐指数 91.0/100

2. 《段永平投资问答录（商业逻辑篇）》
   作者：段永平、雪球用户 · 评分 8.8 ⭐⭐⭐⭐½ (1762 人评价) · 推荐指数 85.4/100

3. 《大厂小民 : 我在互联网公司的1480天》
   作者：张小满 · 评分 8.5 ⭐⭐⭐⭐½ (898 人评价) · 推荐指数 67.0/100
```

---

## Installation

### Prerequisites

- **Python 3.10** or higher
- **Playwright** (automatically downloaded with `playwright install chromium`)

### Install from source

```bash
# Clone the repository
git clone https://github.com/huisystems/bookrec.git
cd bookrec

# Create and activate a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package and dependencies
pip install -r requirements.txt

# Install Playwright Chromium browser
playwright install chromium
```

### Editable (development) install

```bash
pip install -e .
```

After installation, the `bookrec` command is available on your PATH. You can also run it via:

```bash
python -m src.cli.app
# or
python main.py
```

---

## Authentication

**Douban requires login to fetch tag pages** (as of late 2025). Before running
`bookrec fetch`, do a one-time interactive login:

```bash
bookrec login
```

This command will:
1. Open a **headed** Chromium window pointing at `https://accounts.douban.com/login`
2. Wait for you to complete the login in the browser (username/password or QR code)
3. Wait for you to press **Enter** back in the terminal
4. Save the browser session (cookies + local storage) to a local file as a
   [Playwright `storage_state` JSON](https://playwright.dev/python/docs/auth#reusing-authentication-state)

On every subsequent `bookrec fetch`, `bookrec` loads that storage file into a
new browser context, so you're effectively "already logged in" — no
credentials are stored or transmitted by `bookrec` itself.

### Cookie file location

| Path | Override |
|---|---|
| `~/.config/bookrec/douban_storage.json` (default, created on first `bookrec login`) | `BOOKREC_COOKIE_FILE` environment variable |

### When cookies go stale

Douban sessions expire. If `bookrec fetch` starts returning 0 books with
"检测到豆瓣登录拦截" in stderr, just re-run `bookrec login` to refresh the
session.

### Headless / CI environments

`bookrec login` requires a graphical browser. For headless or CI use you
must either:
- commit a pre-baked storage_state file (treat it like a secret — anyone
  who has it can act as you on Douban), or
- skip the live-Douban check in CI; the project's own CI does this via
  `smoke_fetch.py --skip-if-no-cookie` (see [Releasing](docs/RELEASING.md)).

---

## Usage

### Fetch books from Douban

```bash
# Fetch business and AI books from the last 12 months (default)
bookrec fetch

# Specify categories and time range
bookrec fetch --category 经管,AI --months 12

# Increase pages per tag for more coverage
bookrec fetch --category AI --months 6 --max-pages 5

# Fetch basic info only (skip descriptions and table of contents)
bookrec fetch --no-detail
```

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `-c, --category` | `经管,AI` | Comma-separated categories |
| `-m, --months` | `12` | Fetch books published in the last N months |
| `--max-pages` | `2` | Max pages to scrape per Douban tag |
| `--no-detail` | `false` | Skip detailed info (description, catalog) |

### Generate recommendations

```bash
# Top 10 recommendations across all categories
bookrec recommend

# Top 20 business books with rating >= 8.0
bookrec recommend --top 20 --category 经管 --min-rating 8.0

# Export as Markdown file
bookrec recommend --top 10 --output 推荐.md

# Export as JSON
bookrec recommend --json
```

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `-n, --top` | `10` | Number of recommendations |
| `-c, --category` | all | Filter by category (`经管` or `AI`) |
| `--min-rating` | `7.0` | Minimum rating threshold |
| `--min-rating-count` | `20` | Minimum number of ratings |
| `-o, --output` | (stdout) | Output to a Markdown file |
| `--json` | `false` | Output as JSON |

### Browse the knowledge base

```bash
# List all books in the vault
bookrec list-books

# Filter by category
bookrec list-books --category 经管

# Filter by minimum rating
bookrec list-books --min-rating 8

# Filter by tag
bookrec list-books --tag 机器学习
```

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `-c, --category` | all | Filter by category |
| `--min-rating` | `0` | Minimum rating filter |
| `--tag` | all | Filter by book tag |

### Search books

```bash
# Full-text search across title, author, and description
bookrec search 深度学习
bookrec search "Seymour Papert"
```

### Add notes to a book

```bash
bookrec note <douban_id> Your note text here
```

Each note overwrites the previous note for that book. Notes are stored as Markdown frontmatter in the book file.

### One-time Douban login

```bash
bookrec login
```

See [Authentication](#authentication) above for full details on what
this does and where the session file lives.

### View vault statistics

```bash
bookrec stats
```

Displays total book count, per-category distribution with a visual bar chart, and the vault path.

### View recommendation history

```bash
bookrec history
```

Lists all previously generated recommendation files stored in the vault's `推荐列表/` directory.

### Global options

| Flag | Default | Description |
|------|---------|-------------|
| `--vault` | `./知识库/` | Path to the Obsidian vault (can also be set via `BOOKREC_VAULT`) |
| `--verbose` | `false` | Enable debug-level logging |
| `--help` | | Show help message and exit |

---

## Configuration

Configuration lives in `src/core/config.py`. Key defaults:

| Setting | Default | Description |
|---------|---------|-------------|
| `FETCH_MONTHS` | `12` | Default look-back period for fetching |
| `DEFAULT_TOP_N` | `10` | Default number of recommendations |
| `DEFAULT_MIN_RATING` | `7.0` | Default minimum rating |
| `DEFAULT_MIN_RATING_COUNT` | `20` | Default minimum rating count |
| `VAULT_PATH` | `./知识库/` | Default vault directory |

### Environment variables

| Variable | Description |
|----------|-------------|
| `BOOKREC_VAULT` | Override the default vault path |
| `BOOKREC_COOKIE_FILE` | Override the Douban session storage path (see [Authentication](#authentication)) |

Example:

```bash
export BOOKREC_VAULT=/path/to/my/obsidian/vault
export BOOKREC_COOKIE_FILE=/path/to/douban_storage.json
bookrec fetch
```

---

## Project Structure

```
bookrec/
├── main.py                  # Quick-start entry point
├── pyproject.toml           # Package metadata and build config
├── requirements.txt         # Dependency list
├── smoke_fetch.py           # Manual real-Douban pre-release check (not packaged)
├── CONTRIBUTING.md          # Contributor guide
├── README.md                # This file
├── LICENSE                  # Apache 2.0
│
├── src/
│   ├── cli/
│   │   └── app.py           # Click CLI: 8 commands (login, fetch, recommend, ...)
│   ├── core/
│   │   └── config.py        # Global configuration
│   ├── data_sources/
│   │   ├── base.py          # Abstract data source interface
│   │   └── douban.py        # Douban scraper (Playwright + cookie loading)
│   ├── knowledge/
│   │   └── store.py         # Obsidian vault storage layer
│   ├── models/
│   │   └── book.py          # Book dataclass
│   ├── output/
│   │   └── markdown_gen.py  # Markdown and rating-star generation
│   └── services/
│       ├── orchestrator.py  # Central orchestration logic
│       └── filter.py        # Filtering and ranking engine
│
├── tests/                   # 67 tests, no network dependency
│   ├── test_book_model.py
│   ├── test_cli.py
│   ├── test_douban_anti_scrape.py
│   ├── test_douban_category.py
│   ├── test_filter.py
│   ├── test_markdown_gen.py
│   ├── test_orchestrator.py
│   ├── test_search_note.py
│   └── test_store.py
│
├── docs/                    # Contributor-facing documentation
│   └── RELEASING.md         # Full release runbook
│
└── 知识库/                    # Default Obsidian vault (gitignored)
    ├── 图书/                  # Book entries by category
    ├── 推荐列表/              # Generated recommendation files
    ├── 数据源快照/            # Raw data snapshots
    └── 统计.md               # Auto-updated vault statistics
```

---

## Data Flow

```
Douban (豆瓣)
    │
    ▼
  fetch ──── Playwright scrapes latest and tag pages
    │
    ▼
  dedup ──── Merge by douban_id, skip duplicates
    │
    ▼
  detail ──── Enrich with description and catalog
    │
    ▼
  store ──── Save to Obsidian vault as .md with YAML frontmatter
    │
    ▼
  filter ──── Apply rating, count, and recency thresholds
    │
    ▼
  rank ────── Weighted score = rating * 0.5 + log(rating_count) * 0.3 + recency * 0.2
    │
    ▼
recommend ── Output ranked list as Markdown, JSON, or terminal table
```

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | **Python 3.10+** |
| CLI framework | **Click** 8.x (8 commands: `fetch`, `recommend`, `list-books`, `search`, `note`, `login`, `stats`, `history`) |
| Browser automation | **Playwright** 1.40+ (Chromium) |
| Data serialization | **PyYAML** 6.x |
| Terminal UI | **Rich** 13+ |
| Testing | **Pytest** 7+ (over 60 tests, plus real-Douban `smoke_fetch.py`) |
| Lint / format | **Ruff** (E/W/F/B/I/UP, line-length 100) |
| Storage | **Obsidian-compatible Markdown** with YAML frontmatter |

---

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for our contribution guidelines, which cover:

- Development setup and installation
- Coding standards (PEP 8, type hints, naming conventions)
- Conventional Commits format
- Pull request process and issue reporting

---

## License

This project is licensed under the **Apache License 2.0**. See the [LICENSE](LICENSE) file for details.
