# Polycode Monorepo — Coding Agent Guidelines

Instructions for AI coding agents (Claude Code, Cursor, etc.) working in this repository.

---

## Project Overview

| App        | Stack                                                   |
| ---------- | ------------------------------------------------------- |
| `polycode` | Python 3.13, CrewAI, FastAPI, Celery, Redis, PostgreSQL |
| `landing`  | React 19, TypeScript, Vite, Tailwind CSS 4              |

---

## Build / Lint / Test Commands

### apps/polycode (Python)

```bash
cd apps/polycode

uv sync                                        # Install dependencies
uv run ruff check --fix . && uv run ruff format .  # Lint and format
uv run pyright                                 # Type check

uv run pytest                                  # Run all tests
uv run pytest tests/test_flows.py              # Run single test file
uv run pytest tests/test_flows.py::test_name   # Run single test
uv run pytest -k "pattern"                     # Run tests matching pattern

uv run python -m cli.main                      # CLI entry point
uv run uvicorn github_app.app:app --reload     # FastAPI server
make docker                                    # Build and push container
```

### apps/landing (TypeScript/React)

```bash
cd apps/landing
pnpm install && pnpm dev                       # Install and run dev
pnpm build                                     # Build (tsc -b && vite build)
pnpm lint                                      # Run ESLint
```

---

## Code Style — Python

**Linting (ruff)**: Line length 120, Rules `E/F/I/N/W` (E501 ignored)

**Imports** (alphabetical within groups):

```python
"""Module docstring."""
# 1. Standard library
import logging
from typing import Any
# 2. Third-party
from crewai import Agent, Crew, Task
# 3. Local imports
from project_manager.types import Issue
```

**Type Annotations** (Python 3.10+):

```python
def get_issue(self, issue_id: int) -> Issue | None:  # Prefer | over Optional
labels: list[str] = []
config: dict[str, Any] = {}
```

**Naming Conventions**:

- Classes: PascalCase (`GitHubProjectManager`)
- Functions/variables: snake_case (`get_open_issues`)
- Constants: UPPER_SNAKE_CASE (`MERGE_REQUIRED_LABEL`)
- Private methods: underscore prefix (`_prepare_work_tree`)

**Error Handling & Logging**:

```python
log = logging.getLogger(__name__)

if not token:
    raise ValueError("GitHub token required via config or GITHUB_TOKEN env var")

try:
    issue = self.repo.get_issue(issue_number)
except Exception as e:
    log.error(f"🚨 Failed: {e}")
    return []

log.info(f"🏹 Created worktree at: {path}")
```

**Testing (AAA Pattern)**:

```python
def test_get_flow_for_label_priority():
    """Test that higher priority flow wins when multiple match."""
    # Arrange
    registry = get_module_registry().flow_registry
    # Act
    registry.register(FlowDef(name="priority-flow", ...))
    flow = registry.get_flow_for_label("polycode:implement")
    # Assert
    assert flow is not None
```

---

## Code Style — TypeScript/React

```tsx
// Imports: 1. React/external, 2. Internal (alphabetical)
import { useState } from "react";
import { ThemeToggle } from "./ThemeToggle";

export function Header() {} // Named for components
export default function Home() {} // Default for pages
```

**Naming**: Components PascalCase (`Header`), variables camelCase (`navItems`), handlers `handleClick`, boolean state `isLoading`

**Tailwind** (order: layout → sizing → spacing → typography → colors → effects):

```tsx
<div className="flex w-full flex-col gap-4 px-4 text-muted-foreground hover:bg-accent">
<div className="bg-background text-foreground">  // Use theme variables
```

---

## Pre-commit Hooks

Configured in `.pre-commit-config.yaml`: trailing-whitespace, autoflake, commitizen+gitmoji, markdownlint, pyright

Run: `pre-commit run --all-files`

---

## Project Structure

```
polycode/
├── apps/
│   ├── polycode/                    # Python backend
│   │   ├── src/{cli,crews,flows,github_app,persistence,project_manager,tools}/
│   │   └── tests/
│   └── landing/                     # React frontend
│       └── src/{components,pages}/
├── AGENTS.md                        # This file
├── apps/polycode/AGENTS.md          # Detailed Python patterns
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

## Key References

- **CrewAI**: `apps/polycode/AGENTS.md` and `apps/polycode/src/AGENTS.md`
- **CrewAI docs**: <https://docs.crewai.com> — check version before writing
- **Tailwind**: Use theme variables (`bg-background`, `text-foreground`)
