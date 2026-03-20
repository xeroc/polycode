# Polycode — Coding Agent Guidelines

Instructions for AI coding agents (Claude Code, Cursor, etc.) working in this repository.

---

## Project Overview

Multi-agent software development automation using CrewAI. GitHub App integration for
webhook-driven workflows across multiple repositories.

**Stack:** Python 3.13, CrewAI, FastAPI, Celery, Redis, PostgreSQL, Pydantic

---

## Build / Lint / Test Commands

### Package Management

```bash
uv sync                   # Install dependencies
uv add <package>          # Add dependency
uv lock                   # Update lock file
```

### Linting & Type Checking

```bash
uv run ruff check .                    # Lint all files
uv run ruff check --fix .              # Auto-fix lint errors
uv run ruff format .                   # Format code
uv run pyright                         # Type check (via pre-commit)
```

### Testing

```bash
uv run pytest                                        # Run all tests
uv run pytest tests/test_github_manager.py           # Run single test file
uv run pytest tests/test_github_manager.py::test_has_label_returns_true_when_label_exists  # Single test
uv run pytest -k "label"                             # Run tests matching pattern
uv run pytest -v                                     # Verbose output
```

### Running the Application

```bash
uv run python -m project_manager.cli    # CLI entry point
uv run uvicorn github_app.app:app       # FastAPI webhook server
```

### Docker

```bash
make docker       # Build and push (uses timestamp as version)
```

---

## Code Style Guidelines

### Linting Rules (ruff)

- Line length: 79 characters
- Enabled rules: E, F, I, N, W (E501 ignored)
- Always run `uv run ruff check --fix .` before committing

### Imports

```python
"""Module docstring."""

# 1. Standard library (alphabetical)
import json
import logging
import os
import re
from pathlib import Path
from typing import Optional, TypeVar

# 2. Third-party (alphabetical)
import git
from crewai import Flow
from pydantic import BaseModel, Field

# 3. Local imports (alphabetical)
from glm import GLMJSONLLM
from persistence.postgres import SessionLocal
from project_manager.types import ProjectConfig
```

### Type Annotations

Use modern Python 3.10+ syntax:

```python
# Prefer union syntax
def get_issue(self, issue_id: int) -> Issue | None:

# Over Optional
def get_issue(self, issue_id: int) -> Optional[Issue]:

# List/dict generics without importing from typing
labels: list[str] = []
config: dict[str, Any] = {}
```

### Pydantic Models

```python
class ProjectConfig(BaseModel):
    """Configuration for a project manager."""

    provider: str
    repo_owner: str
    repo_name: str
    project_identifier: str | None = None
    token: str | None = None
    extra: dict[str, Any] = {}
```

- Always include docstrings for classes
- Use `Field()` for field descriptions when helpful
- Use `| None` for optional fields with defaults

### Naming Conventions

```python
# Classes: PascalCase
class GitHubProjectManager:

# Functions/methods: snake_case
def get_open_issues(self) -> list[Issue]:

# Variables: snake_case
project_items = []

# Constants: UPPER_SNAKE_CASE
MERGE_REQUIRED_LABEL = "approved"

# Private methods: prefix with underscore
def _prepare_work_tree(self):

# Properties for lazy-loaded values
@property
def project_id(self) -> str:
```

### Error Handling

```python
# Raise specific exceptions with helpful messages
if not token:
    raise ValueError(
        "GitHub token must be provided via config or GITHUB_TOKEN env var"
    )

# Handle exceptions gracefully, return sensible defaults
try:
    result = self.projects_client.get_project_id(owner, number)
except github.UnknownObjectException:
    log.warning(f"Project not found for {owner}")
    return []

# Log errors with context
except Exception as e:
    log.error(f"Failed to update PostgreSQL status: {e}")
```

### Logging

```python
import logging

log = logging.getLogger(__name__)

# Use emoji prefixes for visual scanning in logs
log.info(f"🏹 Created worktree at: {worktree_path}")
log.warning(f"⚠️ No test command, skipping verification")
log.error(f"🚨 Failed to ensure request exists: {e}")
```

### Docstrings

```python
def get_open_issues(self) -> list[Issue]:
    """Get all open issues from the repository.

    Returns:
        List of open issues
    """

def __init__(self, config: ProjectConfig) -> None:
    """Initialize GitHub project manager.

    Args:
        config: Project configuration

    Raises:
        ValueError: If token is not provided
    """
```

### Testing Patterns

```python
"""Test module docstring."""

from unittest.mock import MagicMock

from project_manager.github import GitHubProjectManager
from project_manager.types import ProjectConfig


def test_has_label_returns_true_when_label_exists():
    """Test that has_label returns True when the label is present."""
    # Arrange
    config = ProjectConfig(
        repo_owner="testowner",
        repo_name="testrepo",
        token="fake_token",
    )
    manager = GitHubProjectManager(config)
    mock_repo = MagicMock()
    mock_pr = MagicMock()
    mock_pr.labels = [MagicMock(name="approved")]
    mock_repo.get_pull.return_value = mock_pr
    manager.github_client.get_repo = MagicMock(return_value=mock_repo)

    # Act
    result = manager.has_label(123, "approved")

    # Assert
    assert result is True
    mock_repo.get_pull.assert_called_once_with(123)
```

- Use descriptive test names: `test_<method>_<scenario>_<expected_result>`
- AAA pattern: Arrange, Act, Assert
- Use `unittest.mock` for mocking

---

## Project Structure

```
polycode/
├── src/
│   ├── project_manager/    # GitHub project management
│   ├── github_app/         # GitHub App webhook server
│   ├── celery_tasks/       # Async task processing
│   ├── persistence/        # Database layer
│   ├── feature_dev/        # Feature development crew
│   └── flowbase.py         # Base flow classes
├── tests/                  # Test files
├── pyproject.toml          # Project config
└── .env                    # Environment variables
```

---

## Pre-commit Hooks

Configured in `.pre-commit-config.yaml`:

- trailing-whitespace
- commitizen (conventional commits with gitmoji)
- markdownlint
- pyright (type checking)

Run manually: `pre-commit run --all-files`

---

## Environment Variables

Required in `.env`:

```
GITHUB_TOKEN=ghp_...
DATABASE_URL=postgresql://...
REDIS_HOST=localhost
REDIS_PORT=6379
OPENAI_API_KEY=sk-...
OPENAI_URL_BASE=http://...
```

---

## CrewAI Reference

See `src/AGENTS.md` for detailed CrewAI patterns, agent/task configuration, and flows.

**Key points:**

- Use `crewai.LLM` or string shorthand like `"openai/gpt-4o"`
- Agents and tasks in YAML configs
- `@CrewBase` decorator on crew classes
- `# type: ignore[index]` for config dictionary access
