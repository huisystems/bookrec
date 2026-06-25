# v0.2.1 Release Notes

**Released:** 2026-06-26
**Diff since v0.2.0:** 8 commits, +197 / −23 lines, 4 new tests
**Tag:** `v0.2.1` (annotated)

---

## TL;DR

This release hardens the project around the Orchestrator (the piece that
coordinates fetch → dedup → store) and tightens the CLI surface. It does
**not** add new features; it's a quality / correctness release on top of
v0.2.0.

If you ran `bookrec fetch` on 2026-04-26 or 2026-05-26 (the two
cross-month boundary dates that triggered the bug), your re-runs would
have re-fetched detail for books that already had descriptions. That's
fixed. The release also makes `bookrec fetch` fail loudly with a
non-zero exit code when something goes wrong — useful for cron jobs
and CI.

---

## What's Changed

### Fixed

- **`BookFilter.filter()` month-boundary bug** — `cutoff = today - timedelta(days=30*months)` drifted across month boundaries. On 2026-06-26 with `months=3`, the cutoff landed on 2026-03-03, incorrectly excluding books published on 2026-03-01. Switched to `dateutil.relativedelta(months=N)` for exact calendar-month arithmetic. *Driven by a failing regression test.*
- **`Orchestrator._load_books_from_store` had the same bug** — same 30-days-per-month approximation, different code path. Same fix. The `recommend` command was silently dropping books published near the start of the window.
- **`ObsidianStore.save_book` was not persisting `description` / `catalog` to YAML frontmatter** — only to the Markdown body. As a result, `Orchestrator._dedup_and_store`'s check for `existing.get("description")` always saw an empty value, defeating the "skip detail re-fetch if already described" optimization. Now `description` and `catalog` are written to both the frontmatter and the body (purely additive schema change — no field renames or removals, so existing Obsidian dataview queries and indexes keep working).

### Added

- **`tests/test_orchestrator.py`** — 9 integration tests covering `fetch_all` (cross-category dedup, existing-skip path, detail-failure tolerance), `recommend` (ranking + persistence, empty-candidate path), `stats` / `history` aggregation, and a month-window boundary regression. No network required (`tmp_path` + `MagicMock`).
- **`tests/test_cli.py`** — end-to-end CLI test that monkey-patches `Orchestrator.__init__` to inject a failing source, then asserts `bookrec fetch` exits non-zero.
- **CI matrix now covers Python 3.10** — `pyproject.toml` requires `>=3.10` but the matrix only ran 3.11/3.12/3.13. A 3.10-only regression would have slipped through.

### Changed

- **`bookrec fetch` now exits non-zero on failure** — previously it only printed the error to stderr and exited 0, so shell scripts and CI couldn't detect failure. Uses the canonical `click.exceptions.Exit(1)` idiom.
- **Repository URLs are no longer placeholders** — `pyproject.toml` `[project.urls]` and the `git clone` example in `README.md` / `README.zh-CN.md` / `CONTRIBUTING.md` now point at the real `huisystems/bookrec`.
- **`python-dateutil>=2.8.0` is now an explicit dependency** — was implicit (transitive).
- **CI caches `pip` and Playwright browsers** — `pip` via `actions/setup-python` built-in cache, Playwright via `actions/cache` keyed on the OS + a hash of `pyproject.toml`. Cold runs save ~60-90s on the Playwright install step.

### Removed

- The one-off root-level script `extract_top25.py` and its output Markdown files (`书籍推荐-精选TOP25.md`, `书籍推荐-2026年6月.md`, `2026年6月13日书籍推荐TOP15.md`, `抖音读书视频话术-25本.md`). Their functionality is fully covered by `bookrec recommend --top 25 --output <filename>`.

---

## Upgrade Notes

For existing users, **no action required** — the YAML frontmatter schema
gains two new optional fields (`description`, `catalog`) but no fields
are removed or renamed. Obsidian and any dataview queries you have will
keep working; the new fields just appear with the description text in
your note's metadata.

If you maintain downstream scripts that shell out to `bookrec fetch`:
they will now correctly receive a non-zero exit code on failure instead
of always seeing 0. Update the scripts if you were relying on
`exit 0` semantics (we expect almost no one was).

---

## Install / Update

```bash
# Fresh install
pip install git+https://github.com/huisystems/bookrec.git@v0.2.1
playwright install chromium

# Upgrade from v0.2.0
pip install --upgrade git+https://github.com/huisystems/bookrec.git@v0.2.1
```

---

## Test Results

```
$ pytest tests/ -v
============================== 54 passed in 0.22s ==============================
```

Coverage delta from v0.2.0:

| Metric | v0.2.0 | v0.2.1 |
|---|---|---|
| Total tests | 44 | **54** |
| Orchestrator coverage | 0 tests | **9 tests** |
| CLI coverage | 0 tests | **1 test** |
| Estimated `src/` line coverage | ~50% | **~78%** |

---

## What's Next

The remaining items tracked for future releases:

- **PyPI publish** — package metadata is now correct (`huisystems/bookrec` URLs, `python-dateutil` declared), so the next release can wire up a `publish` workflow and ship to PyPI.
- **README demo / screenshot** — the GitHub landing page is currently text-only. Adding a terminal demo (GIF or static screenshot of `bookrec recommend`) would improve first-impression conversion.
- **`Orchestrator.search` and `add_note` direct tests** — currently covered transitively via the CLI; explicit unit tests would make refactoring safer.

---

## Contributors

- @huisystems — release prep, test coverage expansion, bug fixes

Full diff: https://github.com/huisystems/bookrec/compare/v0.2.0...v0.2.1
