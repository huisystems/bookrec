#!/usr/bin/env python3
"""Smoke test: end-to-end fetch against real Douban.

NOT a unit test, NOT committed to the repo's tests/ directory. Lives
at the project root and is meant to be run manually before releases
to confirm Playwright + 豆瓣 page structure + orchestrator all still
talk to each other correctly.

Usage:
    .venv/bin/python smoke_fetch.py                       # fail if no cookie
    .venv/bin/python smoke_fetch.py --skip-if-no-cookie   # exit 0 if no cookie

What it does:
  1. Creates a fresh tmp vault (does not touch the project's 知识库/)
  2. If --skip-if-no-cookie and config.COOKIE_FILE does not exist:
     print a warning and exit 0 (for CI environments without a logged-in
     Douban session)
  3. Invokes the real CLI: bookrec fetch --vault <tmp> --category AI
        --max-pages 1
  4. Asserts the CLI exits 0, returns a non-zero book count
  5. Asserts at least one book .md file is written into the tmp vault
  6. Cleans up the tmp vault on success or failure

Exit codes:
  0   fetch succeeded, found >=1 book (or skipped per --skip-if-no-cookie)
  1   fetch failed (network error, captcha, selector broken, etc.)
  2   fetch returned 0 books (page structure may have changed)
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--skip-if-no-cookie",
        action="store_true",
        help="Exit 0 (with warning) if config.COOKIE_FILE does not exist. "
        "Intended for CI environments without a logged-in Douban session.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent
    venv_python = repo_root / ".venv" / "bin" / "python"

    if not venv_python.exists():
        print(f"ERROR: {venv_python} not found. Run from the project root with .venv/ active.")
        return 1

    # Lazy-import config so we can skip before importing playwright/click
    from src.core import config

    if args.skip_if_no_cookie and not Path(config.COOKIE_FILE).exists():
        print(
            f"SKIP: --skip-if-no-cookie set, but {config.COOKIE_FILE} not found. "
            f"CI environments without a logged-in Douban session should expect this. "
            f"Run 'bookrec login' locally before tagging a release."
        )
        return 0

    tmp_vault = Path(tempfile.mkdtemp(prefix="bookrec-smoke-"))
    try:
        print(f"=== smoke_fetch: vault = {tmp_vault}")

        result = subprocess.run(
            [
                str(venv_python),
                "-m",
                "src.cli.app",
                "--vault",
                str(tmp_vault),
                "fetch",
                "--category",
                "AI",
                "--max-pages",
                "1",
            ],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=120,
        )

        print("--- stdout ---")
        print(result.stdout)
        if result.stderr:
            print("--- stderr ---")
            print(result.stderr)

        if result.returncode != 0:
            print(f"\nFAIL: CLI exited with code {result.returncode}")
            return 1

        # Inspect vault
        book_files = list((tmp_vault / "图书" / "AI").glob("*.md"))
        book_files = [f for f in book_files if f.name != "__索引.md"]
        n_books = len(book_files)

        print(f"\nbooks written: {n_books}")

        if n_books == 0:
            print("FAIL: fetch returned 0 books — page structure may have changed")
            return 2

        # Spot-check: first book's frontmatter should have title + douban_id
        first = book_files[0]
        content = first.read_text(encoding="utf-8")
        if "douban_id:" not in content or "title:" not in content:
            print(f"FAIL: {first.name} missing frontmatter fields")
            print(content[:500])
            return 1

        # Detail fetch (not --no-detail) should populate 简介 section
        if "## 简介" not in content:
            # Not a hard failure: maybe the book's detail page legitimately
            # has no description, or captcha kicked in. Just report.
            print(f"WARN: {first.name} has no 简介 section — detail fetch may have failed")
        else:
            print(f"OK: {first.name} has 简介 section (detail fetch worked)")

        print(f"OK: {first.name} written with frontmatter")
        return 0

    except subprocess.TimeoutExpired:
        print("\nFAIL: fetch timed out after 120s — likely a hang, not a transient error")
        return 1
    finally:
        shutil.rmtree(tmp_vault, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
