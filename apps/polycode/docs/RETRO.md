# Retro Integration Plan

> **Status**: Planning (v4 — aligned with PLUGIN.md + INJECT.md)
> **Date**: 2026-04-01

## Core Decisions

1. **One retro per commit** — attached via git-notes right after gitcore commits on `STORY_COMPLETED`
2. **Git-notes ONLY** — no PostgreSQL. Delete `retro/persistence.py` entirely
3. **Retro hooks run AFTER gitcore hooks** — use `@hookimpl(trylast=True)` to guarantee ordering
4. **RetroModule depends on gitcore** — registered after gitcore in bootstrap
5. **Retro crew lives in `src/retro/crews/retro_crew/`** — not in `src/crews/`
6. **Context via `get_context_collectors()`** — plain `(name, callable)` tuples per INJECT.md

---

## Current State

### What exists

| File                       | Status    | Notes                                                     |
| -------------------------- | --------- | --------------------------------------------------------- |
| `src/retro/types.py`       | KEEP      | `RetroEntry`, `RetroQuery`, `ActionableItem`              |
| `src/retro/analyzer.py`    | REFACTOR  | Depends on `RetroStore` (postgres). Refactor to git-notes |
| `src/retro/persistence.py` | DELETE    | No postgres. Git-notes only                               |
| `src/retro/git_notes.py`   | DELETE    | Canonical `GitNotes` is `gitcore/notes.py`                |
| `src/retro/__init__.py`    | UPDATE    | Remove dead exports                                       |
| `src/retro/README.md`      | REFERENCE | Design doc                                                |

### Infrastructure already in place (from PLUGIN.md + INJECT.md)

**Module protocol** (`src/modules/protocol.py`):

- `get_context_collectors() -> list[tuple[str, Callable]]` — modules return `(name, fn)` pairs
- No protocol class needed. Plain callables that take `state` and return `dict[str, Any]`

**ContextRegistry** (`src/modules/registry.py`):

- Lives inside `ModuleRegistry` as `module_registry.context_registry`
- `register(name, fn)` — register a named collector
- `collect_all(state) -> dict[str, Any]` — run all collectors, merge results
- `collect_from_modules(modules)` — auto-collect from all module `get_context_collectors()` returns
- Failures isolated (logged + skipped). Key collisions warned.

**Flow base** (`src/flows/base.py`):

- `FlowIssueManagement.use_context_registry(registry)` — wire at bootstrap
- `self.injected_content() -> dict[str, Any]` — convenience method, delegates to registry

**Bootstrap** (`src/bootstrap.py`):

- `module_registry.context_registry.collect_from_modules(module_registry.modules)` — after `load_all()`
- `FlowIssueManagement.use_context_registry(module_registry.context_registry)` — wire into flows

### Hook ordering

```
STORY_COMPLETED event fires
    │
    ├── gitcore hooks (commit + push)        ← must run FIRST
    │
    └── retro hooks (attach git-note)        ← must run AFTER commit

pluggy default: LIFO (last registered = first called)
  gitcore registered first → called LAST by default ❌

Solution: retro uses @hookimpl(trylast=True) ✅
  This guarantees retro runs after all regular hooks including gitcore
```

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                       Flow Execution                         │
│                              │                               │
│                      STORY_COMPLETED                         │
│                              │                               │
│                ┌─────────────┴─────────────┐                 │
│                ▼                           ▼                 │
│       ┌─────────────────┐        ┌──────────────────┐        │
│       │  GitcoreHooks   │        │   RetroHooks     │        │
│       │  (commit+push)  │        │  (trylast=True)  │        │
│       └─────────────────┘        └────────┬─────────┘        │
│                                           │                  │
│                                ┌──────────┴──────────┐      │
│                                ▼                     ▼      │
│                         ┌────────────┐    ┌─────────────┐    │
│                         │  git-notes │    │  RetroCrew  │    │
│                         │ (refs/     │    │ (Phase 3)   │    │
│                         │  notes/    │    └─────────────┘    │
│                         │  retros)   │                       │
│                         └────────────┘                       │
│                                                              │
│   ─ ─ ─ ─ ─ Context Collectors (INJECT.md) ─ ─ ─ ─ ─ ─    │
│                                                              │
│   self.injected_content()                                    │
│       │  delegates to ContextRegistry.collect_all(state)     │
│       │                                                      │
│       ├── agentsmd collector  → "agents_md", "agents_md_map"│
│       ├── retro collector     → "retro_context"              │
│       └── (future)           → ...                           │
│                                                              │
│   → merged dict spread into crew kickoff(inputs={**injected})│
└──────────────────────────────────────────────────────────────┘
```

---

## Phase 1: Module + Git-Notes Retro

### 1.1 — Delete files

| File                       | Reason                                     |
| -------------------------- | ------------------------------------------ |
| `src/retro/persistence.py` | No postgres. Git-notes only                |
| `src/retro/git_notes.py`   | Canonical `GitNotes` is `gitcore/notes.py` |

### 1.2 — Refactor `src/retro/analyzer.py`

Remove `RetroStore` dependency. Read retros from git-notes:

```python
"""Retro pattern analysis — reads from git-notes, not postgres."""

import logging
from collections import Counter

from gitcore import GitNotes
from gitcore.types import GitContext

from .types import RetroEntry

logger = logging.getLogger(__name__)

RETRO_NOTES_REF = "refs/notes/retros"


class PatternAnalyzer:
    """Analyze retrospectives stored as git-notes."""

    def __init__(self, repo_path: str) -> None:
        self.repo_path = repo_path
        self._notes = GitNotes(
            GitContext(repo_path=repo_path),
            notes_ref=RETRO_NOTES_REF,
        )

    def get_recent_retros(self, limit: int = 10) -> list[RetroEntry]:
        shas = self._notes.list_all()
        retros = []
        for sha in shas[-limit:]:
            entry = self._notes.show(RetroEntry, commit_sha=sha)
            if entry:
                retros.append(entry)
        return retros

    def generate_context_injection(self, limit: int = 5) -> str:
        retros = self.get_recent_retros(limit)
        if not retros:
            return ""

        recent_failures = [r for r in retros if r.retro_type == "failure"]
        context = [
            f"## Previous Retrospectives ({len(retros)} total)",
            "",
            "### Recent Failures",
        ]
        for r in recent_failures[:3]:
            context.append(f"- **Commit {r.commit_sha[:8]}**: {r.retro_type}")
            if r.what_failed:
                context.append(f"  Failed: {r.what_failed[0][:60]}...")

        top_issues = self._extract_top_issues(retros, limit=3)
        if top_issues:
            context.extend(["", "### Recurring Issues"])
            for issue, count in top_issues.items():
                context.append(f"- {issue} ({count}x)")

        return "\n".join(context)

    def _extract_top_issues(
        self, retros: list[RetroEntry], limit: int = 5
    ) -> dict[str, int]:
        all_failures: list[str] = []
        for r in retros:
            all_failures.extend(r.what_failed)
        counter = Counter(all_failures)
        return dict(counter.most_common(limit))
```

### 1.3 — Create `src/retro/module.py`

Follows `RalphModule` / `GitcoreModule` pattern:

```python
"""Retro module — continuous improvement via git-notes retrospectives."""

import logging
from typing import Any

import pluggy
from modules.context import ModuleContext

log = logging.getLogger(__name__)


class RetroModule:
    """Retro module: per-commit retrospectives attached via git-notes."""

    name: str = "retro"
    version: str = "0.1.0"
    dependencies: list[str] = ["gitcore"]

    @classmethod
    def on_load(cls, context: ModuleContext) -> None:
        log.info(f"📦 Retro module loaded (v{cls.version})")

    @classmethod
    def register_hooks(cls, hook_manager: pluggy.PluginManager) -> None:
        from retro.hooks import RetroHooks

        hook_manager.register(RetroHooks())
        log.info("🏹 Registered RetroHooks")

    @classmethod
    def get_models(cls) -> list[type]:
        return []

    @classmethod
    def get_context_collectors(cls) -> list[tuple[str, Any]]:
        return [("retro", cls._collect_retro_context)]

    @classmethod
    def _collect_retro_context(cls, state: Any) -> dict[str, Any]:
        repo = getattr(state, "repo", None)
        if not repo:
            return {"retro_context": ""}

        from retro.analyzer import PatternAnalyzer

        analyzer = PatternAnalyzer(repo)
        context = analyzer.generate_context_injection(limit=5)
        return {"retro_context": context}
```

### 1.4 — Create `src/retro/hooks.py`

```python
"""Hook implementations for retro module.

Uses trylast=True to guarantee retro runs AFTER gitcore commit+push.
"""

import logging
import subprocess

from modules.hooks import FlowEvent, hookimpl

log = logging.getLogger(__name__)

RETRO_NOTES_REF = "refs/notes/retros"


class RetroHooks:
    """Lifecycle hooks for retrospective generation."""

    @hookimpl(trylast=True)
    def on_flow_event(self, event, flow_id, state, result, label):
        if event == FlowEvent.STORY_COMPLETED:
            self._retro_on_commit(flow_id, state, result)

        if event == FlowEvent.FLOW_ERROR:
            self._retro_on_failure(flow_id, state, result)

    def _retro_on_commit(self, flow_id, state, story):
        from gitcore import GitNotes
        from gitcore.types import GitContext
        from retro.types import RetroEntry

        commit_sha = self._get_head_sha(state.repo)
        retro = RetroEntry(
            commit_sha=commit_sha,
            flow_id=flow_id,
            story_id=getattr(story, "id", None),
            story_title=getattr(story, "title", None),
            repo_owner=state.repo_owner or "",
            repo_name=state.repo_name or "",
            retro_type="success",
            what_worked=self._extract_successes(story),
            what_failed=getattr(story, "errors", []),
            root_causes=[],
            actionable_improvements=[],
            retry_count=len(getattr(story, "errors", [])),
        )

        notes = GitNotes(
            GitContext(repo_path=state.repo),
            notes_ref=RETRO_NOTES_REF,
        )
        notes.add(model=retro, force=True)
        log.info(f"📝 Retro attached to commit {commit_sha[:8]}")

    def _retro_on_failure(self, flow_id, state, error):
        from gitcore import GitNotes
        from gitcore.types import GitContext
        from retro.types import RetroEntry

        commit_sha = self._get_head_sha(state.repo)
        retro = RetroEntry(
            commit_sha=commit_sha,
            flow_id=flow_id,
            repo_owner=state.repo_owner or "",
            repo_name=state.repo_name or "",
            retro_type="failure",
            what_worked=[],
            what_failed=[str(error)[:200]],
            root_causes=[],
            actionable_improvements=[],
        )

        notes = GitNotes(
            GitContext(repo_path=state.repo),
            notes_ref=RETRO_NOTES_REF,
        )
        notes.add(model=retro, force=True)
        log.info(f"📝 Failure retro attached to commit {commit_sha[:8]}")

    @staticmethod
    def _get_head_sha(repo_path: str) -> str:
        result = subprocess.run(
            ["git", "-C", repo_path, "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()

    @staticmethod
    def _extract_successes(story) -> list[str]:
        if not hasattr(story, "errors") or not story.errors:
            return ["All tests passed"]
        return []
```

### 1.5 — Update `src/retro/__init__.py`

```python
"""Retro module — continuous improvement via git-notes retrospectives."""

from retro.types import ActionableItem, RetroEntry, RetroQuery

__all__ = ["RetroEntry", "RetroQuery", "ActionableItem"]
```

### 1.6 — Register in `src/bootstrap.py`

Add after gitcore registration:

```python
from retro.module import RetroModule
module_registry.register_builtin(RetroModule)
```

The `collect_from_modules()` call already exists in bootstrap and will pick up
retro's `get_context_collectors()` automatically:

```python
module_registry.context_registry.collect_from_modules(module_registry.modules)
```

---

## Phase 2: Wire Context into Flows

**The infrastructure already exists** (INJECT.md is implemented). This phase is about
making flows use `self.injected_content()` consistently so retro context reaches crews.

### What `injected_content()` returns

When retro is registered, calling `self.injected_content()` returns:

```python
{
    "agents_md": "...",          # from agentsmd module
    "agents_md_map": {...},      # from agentsmd module
    "retro_context": "## Previous Retrospectives\n...",  # from retro module
}
```

### Changes to `src/flows/ralph/flow.py`

```python
# In plan() and implement() methods:

injected = self.injected_content()
agents_md_map = injected.pop("agents_md_map", {})

result = (
    PlanCrew()
    .crew(agents_md_map=agents_md_map)
    .kickoff(inputs=dict(
        task=self.state.task[:120],
        repo=self.state.repo,
        branch=self.state.branch,
        **injected,                          # agents_md + retro_context + future
        file_in_repos=self.git_operations.list_tree(),
    ))
)
```

### Changes to task YAML files

Add `{retro_context}` placeholder where helpful:

```yaml
# plan_crew/tasks.yaml
description: >
  Analyze the following task and break it into stories:
  {task}

  Repository: {repo}
  Branch: {branch}

  {retro_context}
```

When no retros exist yet, `retro_context` is empty string — no effect.

### Changes required

| File                        | Change                                                  |
| --------------------------- | ------------------------------------------------------- |
| `src/flows/ralph/flow.py`   | Use `self.injected_content()` in plan() and implement() |
| `src/flows/specify/flow.py` | Same pattern                                            |
| Crew task YAML files        | Add `{retro_context}` placeholder where useful          |

---

## Phase 3: Retro Crew (LLM-powered analysis)

### Structure

```
src/retro/crews/retro_crew/
├── config/
│   ├── agents.yaml
│   └── tasks.yaml
├── retro_crew.py
└── __init__.py
```

### When to use

Data-driven retros (Phase 1) capture facts. The LLM crew adds:

- Root cause analysis
- Actionable improvement suggestions
- Pattern correlation across commits

Wire into hooks:

```python
def _retro_on_commit(self, flow_id, state, story):
    # Phase 1: data-driven retro
    retro = self._build_data_retro(flow_id, state, story)

    # Phase 3: enhance with LLM analysis (optional, behind flag)
    from retro.crews.retro_crew import RetroCrew
    enhanced = RetroCrew().crew().kickoff(inputs={
        "execution_data": retro.model_dump_json(),
        "past_retros": analyzer.generate_context_injection(limit=3),
    })
    if enhanced.pydantic:
        retro = enhanced.pydantic  # type: ignore

    notes.add(model=retro, force=True)
```

---

## File Changes Summary

### New files

| File                  | Purpose                                              |
| --------------------- | ---------------------------------------------------- |
| `src/retro/module.py` | `RetroModule` implementing `PolycodeModule` protocol |
| `src/retro/hooks.py`  | `RetroHooks` with `@hookimpl(trylast=True)`          |

### Deleted files

| File                       | Reason                                     |
| -------------------------- | ------------------------------------------ |
| `src/retro/persistence.py` | No postgres. Git-notes only                |
| `src/retro/git_notes.py`   | Canonical `GitNotes` is `gitcore/notes.py` |

### Modified files

| File                        | Change                                                    |
| --------------------------- | --------------------------------------------------------- |
| `src/retro/__init__.py`     | Remove dead exports (`GitNotes`, `RetroStore`, `init_db`) |
| `src/retro/analyzer.py`     | Refactor: read from git-notes instead of `RetroStore`     |
| `src/bootstrap.py`          | Register `RetroModule` after `GitcoreModule`              |
| `src/flows/ralph/flow.py`   | Use `self.injected_content()` in crew kickoffs            |
| `src/flows/specify/flow.py` | Same pattern                                              |
| Crew task YAML files        | Add `{retro_context}` placeholder                         |

### Unchanged files

| File                      | Why                                                      |
| ------------------------- | -------------------------------------------------------- |
| `src/modules/protocol.py` | `get_context_collectors()` already exists                |
| `src/modules/registry.py` | `ContextRegistry` already exists inside `ModuleRegistry` |
| `src/flows/base.py`       | `injected_content()` already implemented                 |
| `src/retro/types.py`      | Clean, no changes needed                                 |

---

## Execution Order

```
┌──────────────────────────────────────────────────────────────┐
│  Phase 1: Module + Git-Notes Retro                           │
│                                                              │
│  1. DELETE retro/persistence.py, retro/git_notes.py          │
│  2. REFACTOR retro/analyzer.py → git-notes based             │
│  3. CREATE retro/module.py                                   │
│  4. CREATE retro/hooks.py (trylast=True for STORY_COMPLETED) │
│  5. UPDATE retro/__init__.py                                 │
│  6. UPDATE bootstrap.py — register RetroModule               │
│  7. TESTS                                                    │
│                                                              │
│  Verify: uv run pytest tests/                                │
│          uv run ruff check --fix . && uv run ruff format .   │
│          uv run pyright                                      │
├──────────────────────────────────────────────────────────────┤
│  Phase 2: Wire Context into Flows                            │
│                                                              │
│  8.  UPDATE ralph/flow.py — use self.injected_content()      │
│  9.  UPDATE specify/flow.py — same                           │
│  10. UPDATE crew task YAML files — add {retro_context}       │
│  11. TESTS                                                   │
├──────────────────────────────────────────────────────────────┤
│  Phase 3: LLM Retro Crew (optional, deferred)                │
│                                                              │
│  12. CREATE retro/crews/retro_crew/                          │
│  13. WIRE crew into hooks.py for enhanced retros             │
│  14. EVALUATE quality vs data-driven retros                  │
└──────────────────────────────────────────────────────────────┘
```

## Dependency Graph

```
Phase 1 (retro module + git-notes)
    │
    ├── Phase 2 (wire injected_content into flows)
    │       └── retro context collector already works
    │       └── just need flows to use self.injected_content()
    │
    └── Phase 3 (LLM crew, independent of Phase 2)
            └── retro/crews/retro_crew/
```
