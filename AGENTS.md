# Polycode Monorepo — Coding Agent Guidelines

## Project Overview

| App        | Stack                                                   |
| ---------- | ------------------------------------------------------- |
| `polycode` | Python 3.13, CrewAI, FastAPI, Celery, Redis, PostgreSQL |
| `landing`  | React 19, TypeScript, Vite, Tailwind CSS                |

---

## Build / Lint / Test Commands

### apps/polycode (Python)

```bash
cd apps/polycode
uv sync                                        # Install dependencies
uv run ruff check --fix . && uv run ruff format .  # Lint and format
uv run pyright                                 # Type check

uv run pytest                                  # Run all tests
uv run pytest tests/test_file.py               # Run single test file
uv run pytest tests/test_file.py::test_name    # Run single test
uv run pytest -k "pattern"                     # Run tests matching pattern

uv run python -m project_manager.cli           # CLI entry point
uv run uvicorn github_app.app:app --reload     # FastAPI server
```

### apps/landing (TypeScript/React)

```bash
cd apps/landing
pnpm install      # Install dependencies
pnpm dev          # Start dev server
pnpm build        # Build (tsc + vite)
pnpm lint         # Run ESLint
```

---

## Code Style — Python

### Imports (alphabetical within groups)

```python
"""Module docstring."""
# 1. Standard library
import logging
from typing import Any
# 2. Third-party
from crewai import Agent, Crew, Task
from pydantic import BaseModel
# 3. Local imports
from persistence.postgres import SessionLocal
```

### Type Annotations (Python 3.10+)

```python
def get_issue(self, issue_id: int) -> Issue | None:  # Prefer | over Optional
labels: list[str] = []
config: dict[str, Any] = {}
```

### Naming Conventions

- **Classes**: PascalCase (`GitHubProjectManager`)
- **Functions/variables**: snake_case (`get_open_issues`)
- **Constants**: UPPER_SNAKE_CASE (`MERGE_REQUIRED_LABEL`)
- **Private methods**: underscore prefix (`_prepare_work_tree`)

### Error Handling & Logging

```python
if not token:
    raise ValueError("GitHub token required")

log = logging.getLogger(__name__)
log.info(f"🏹 Created worktree at: {path}")
log.warning(f"⚠️ No test command, skipping")
log.error(f"🚨 Failed: {e}")
```

### Testing (AAA Pattern)

```python
def test_method_scenario_expected_result():
    """Test description."""
    # Arrange
    manager = GitHubProjectManager(config)
    # Act
    result = manager.get_issue(123)
    # Assert
    assert result is not None
```

---

## Code Style — TypeScript/React

### Imports

```tsx
// 1. React/external (alphabetical)
import { useState } from "react";
import { Sun, Moon } from "lucide-react";
// 2. Internal (alphabetical)
import { Header } from "./components/Header";
```

### Component Exports

- **Named exports** for components: `export function ComponentName() {}`
- **Default exports** for pages: `export default function PageName() {}`

### Naming Conventions

- **Components**: PascalCase (`Header`)
- **Variables/functions**: camelCase (`navItems`, `toggleTheme`)
- **Event handlers**: handle prefix (`handleClick`)
- **Boolean state**: is/has prefix (`isLoading`, `hasError`)

### Tailwind Class Ordering

```tsx
// Order: layout → sizing → spacing → typography → colors → effects
<div className="flex w-full flex-col gap-4 px-4 text-muted-foreground hover:bg-accent">
<div className="bg-background text-foreground">
```

---

## Linting Rules

**Python (ruff)**: Line length 120, Rules E/F/I/N/W (E501 ignored)
**TypeScript (ESLint)**: TypeScript strict, React hooks, React refresh

## Pre-commit Hooks

Configured in `.pre-commit-config.yaml`: trailing-whitespace, autoflake, commitizen, markdownlint, pyright

Run: `pre-commit run --all-files`

---

## Project Structure

```
polycode/
├── apps/
│   ├── polycode/                    # Python backend
│   │   ├── src/crews/               # CrewAI crew definitions
│   │   ├── src/project_manager/     # GitHub project management
│   │   ├── src/github_app/          # GitHub App webhook server
│   │   └── tests/
│   └── landing/                     # React frontend
├── AGENTS.md                        # This file
├── apps/polycode/AGENTS.md          # Detailed Python/CrewAI patterns
└── apps/polycode/src/AGENTS.md      # CrewAI API reference
```

---

## Environment Variables

```
GITHUB_TOKEN=ghp_...
DATABASE_URL=postgresql://...
REDIS_HOST=localhost
REDIS_PORT=6379
OPENAI_API_KEY=sk-...
```

---

## Key References

- **CrewAI patterns**: `apps/polycode/AGENTS.md`
- **CrewAI API**: `apps/polycode/src/AGENTS.md`
- **CrewAI docs**: <https://docs.crewai.com> — check version before writing
- **Tailwind**: Use theme variables (`bg-background`, `text-foreground`)
