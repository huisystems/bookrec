# Contributing to bookrec

Welcome! We're excited that you're interested in contributing to bookrec, a tool for automated book recommendations.

## Getting Started

1. Fork the repository on GitHub.
2. Clone your fork:
   ```bash
   git clone https://github.com/huisystems/bookrec.git
   cd bookrec
   ```
3. Install the package in editable mode with development dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -e .
   ```
4. Install Playwright browsers required for end-to-end tests:
   ```bash
   playwright install chromium
   ```
5. Run the test suite to verify your setup:
   ```bash
   pytest tests/ -v
   ```

## Development Setup

- **Python**: 3.10 or higher is required.
- **Virtual environment**: Always use a virtual environment to isolate dependencies.
- **Editable install**: `pip install -e .` links the package so changes take effect immediately.
- **Playwright**: Some tests use Playwright for browser automation. Run `playwright install chromium --with-deps` to install system dependencies.

## Coding Guidelines

- **Follow existing patterns**: Match the style and structure of the codebase you see in `src/` and `tests/`.
- **PEP 8**: Adhere to Python's official style guide. Use 4 spaces for indentation.
- **Type hints**: Annotate all function signatures with type hints. Use `from __future__ import annotations` where helpful.
- **Naming**: Use `snake_case` for functions, variables, and modules; `PascalCase` for classes; `UPPER_CASE` for constants.
- **Imports**: Group imports in the order: standard library, third-party packages, local modules. Separate groups with a blank line.

## Testing

- We use `pytest` as the test runner.
- All tests live in the `tests/` directory.
- Run the full test suite before submitting a pull request:
  ```bash
  pytest tests/ -v
  ```
- When adding new functionality, include corresponding tests.
- When fixing a bug, add a test that reproduces the issue before applying the fix.

## Commit Messages

We follow [Conventional Commits](https://www.conventionalcommits.org/). Each commit message should be structured as:

```
<type>: <short summary>

[optional body]
```

Types:

- `feat` — a new feature
- `fix` — a bug fix
- `docs` — documentation changes
- `refactor` — code restructuring without feature changes or bug fixes
- `test` — adding or modifying tests
- `chore` — maintenance tasks (dependencies, tooling, config)

Examples:

```
feat: add support for Goodreads import
fix: resolve crash on empty reading list
docs: update README with new API endpoints
```

## Pull Request Process

1. Create a feature branch from `main`: `git checkout -b feat/my-feature`.
2. Make your changes, following the coding guidelines above.
3. Write or update tests as needed.
4. Run `pytest tests/ -v` and confirm all tests pass.
5. Commit using conventional commit messages.
6. Push your branch and open a pull request against `main`.
7. Fill out the pull request template completely.
8. A maintainer will review your PR. Address any feedback with additional commits.
9. Once approved, a maintainer will merge your changes.

## Reporting Issues

If you encounter a bug or have a suggestion, please use our issue templates:

- [Bug Report](.github/ISSUE_TEMPLATE/bug_report.md) — for reporting bugs
- [Feature Request](.github/ISSUE_TEMPLATE/feature_request.md) — for suggesting new functionality

Before filing, please search the existing issues to avoid duplicates.

---

Thank you for contributing to bookrec!
