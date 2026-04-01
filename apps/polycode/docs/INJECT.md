# Context Collectors

> **Status**: Implemented
> **Depends on**: PLUGIN.md (existing plugin architecture)

## Problem

Context injection into agent tasks was scattered and hardcoded. Flow methods manually threaded `agents_md`, `agents_md_map`, and other values to every crew's `kickoff(inputs=...)`.

## Solution

A **ContextRegistry** collects named callables from modules. Each callable takes a flow state and returns a dict. Before each crew kickoff, `injected_content()` merges all results into the `inputs` dict.

No separate protocol class needed — modules return plain `(name, callable)` tuples, following the same pattern as `FlowRegistry` and `TaskRegistry`.

---

## Architecture

```
                    ┌───────────────────────────────┐
                    │        ModuleRegistry          │
                    │                                │
                    │  _flow_registry: FlowRegistry  │
                    │  _task_registry: TaskRegistry  │
                    │  _context_registry: ContextReg │
                    │                                │
                    │  load_all():                   │
                    │    1. on_load() per module     │
                    │    2. register_hooks()          │
                    │    3. collect flows             │
                    │    4. collect tasks             │
                    │    5. collect context collectors│
                    └───────────────────────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
            ┌──────────────┐ ┌──────────┐ ┌──────────┐
            │ agentsmd     │ │ techstack│ │ custom   │
            │ module       │ │ module   │ │ module   │
            │              │ │ (future) │ │ (plugin) │
            │ collectors:  │ │          │ │          │
            │  agents_md   │ │ keys:    │ │ keys:    │
            │  agents_md_  │ │  tech_   │ │  custom  │
            │  map         │ │  stack   │ │  values  │
            └──────────────┘ └──────────┘ └──────────┘
```

### Data Flow

Flows call `self.injected_content()` which delegates to `ContextRegistry.collect_all(self.state)`. The merged dict is spread into crew inputs:

```python
injected = self.injected_content()
agents_md_map = injected.pop("agents_md_map", {})
result = (
    PlanCrew()
    .crew(agents_md_map=agents_md_map)
    .kickoff(inputs=dict(
        task=self.state.task[:120],
        repo=self.state.repo,
        branch=self.state.branch,
        **injected,
        file_in_repos=self.git_operations.list_tree(),
    ))
)
```

---

## ContextRegistry

**File:** `src/modules/registry.py` (alongside FlowRegistry, TaskRegistry)

```python
class ContextRegistry:
    """Registry for context collectors contributed by modules."""

    def __init__(self) -> None:
        self._collectors: dict[str, Callable[[Any], dict[str, Any]]] = {}

    def register(self, name: str, collect_fn: Callable[[Any], dict[str, Any]]) -> None:
        """Register a named context collector."""

    def collect_all(self, state: Any) -> dict[str, Any]:
        """Run all collectors, merge results. Failures are skipped with warning."""

    def list_collectors(self) -> list[str]:
        """List all registered collector names."""

    def collect_from_modules(self, modules: dict[str, Any]) -> int:
        """Collect collectors from all modules via get_context_collectors()."""
```

### Key Behaviors

- **Fresh on every call** — `collect_all()` runs all collectors each time. No caching.
- **Failure isolation** — a failing collector logs a warning and is skipped. Other collectors still run.
- **Key collision** — if two collectors return the same key, the later one wins and a warning is logged.
- **No protocol** — collectors are plain callables. No `ContextInjector` class or Protocol needed.

---

## Module Hook: `get_context_collectors()`

Modules implement `get_context_collectors()` returning `list[tuple[str, Callable]]`:

```python
from typing import Any

class MyModule:
    name = "my_module"
    version = "0.1.0"
    dependencies: list[str] = []

    @classmethod
    def get_context_collectors(cls) -> list[tuple[str, Any]]:
        """Return context collectors as (name, callable) pairs."""
        return [
            ("my_context", cls._collect_my_context),
        ]

    @classmethod
    def _collect_my_context(cls, state: Any) -> dict[str, Any]:
        """Gather context from flow state."""
        repo = getattr(state, "repo", "")
        return {
            "my_value": f"collected from {repo}",
            "another_key": "...",
        }
```

The callable receives the flow's state model (`BaseFlowModel` or subclass) and must return `dict[str, Any]`. This dict is merged into the crew's `inputs` before kickoff, making the keys available as `{placeholder}` variables in task YAML files.

---

## Built-in: AgentsMD Module

**Directory:** `src/agentsmd/`

Provides the `agents_md` and `agents_md_map` context keys:

```python
# src/agentsmd/module.py

class AgentsMDPolycodeModule:
    name = "agentsmd"
    version = "0.1.0"
    dependencies: list[str] = []

    @classmethod
    def get_context_collectors(cls) -> list[tuple[str, Any]]:
        return [("agents_md", _collect_agents_md)]
```

### What it collects

| Key             | Type             | Description                                       |
| --------------- | ---------------- | ------------------------------------------------- |
| `agents_md`     | `str`            | Root (or first-found) AGENTS.md content           |
| `agents_md_map` | `dict[str, str]` | All AGENTS.md files as `{relative_path: content}` |

### Discovery logic

1. Scans `state.repo` path recursively for `AGENTS.md` files
2. Skips hidden directories (starting with `.`)
3. Uses root `AGENTS.md` if present, otherwise first discovered file
4. Non-existent or missing repo returns empty values

### AGENTS.md Loader Tool

The `AgentsMDLoaderTool` (a CrewAI tool) lives at `src/agentsmd/loader_tool.py`. Crews receive `agents_md_map` and wire it onto agents so they can load specific AGENTS.md files on demand:

```python
from agentsmd.loader_tool import AgentsMDLoaderTool

# In crew class:
if self.agents_md_map:
    tools.append(AgentsMDLoaderTool(agents_md_map=self.agents_md_map))
```

---

## Bootstrap Wiring

**File:** `src/bootstrap.py`

```python
# Register module
from agentsmd import AgentsMDPolycodeModule
module_registry.register_builtin(AgentsMDPolycodeModule)

# Collect context collectors from ALL modules (including agentsmd)
module_registry.context_registry.collect_from_modules(module_registry.modules)

# Wire registry into flow base class
from flows.base import FlowIssueManagement
FlowIssueManagement.use_context_registry(module_registry.context_registry)
```

This happens inside `bootstrap()`, after `module_registry.load_all(context)`.

---

## Flow Base Class

**File:** `src/flows/base.py`

```python
class FlowIssueManagement(Flow[T]):
    _context_registry: ContextRegistry | None = None

    @classmethod
    def use_context_registry(cls, registry: ContextRegistry) -> None:
        cls._context_registry = registry

    def injected_content(self) -> dict[str, Any]:
        if self._context_registry is None:
            return {}
        return self._context_registry.collect_all(self.state)
```

All flows call `self.injected_content()` before crew kickoffs.

---

## Future Extensions

| Collector                  | Keys                         | Source                                                |
| -------------------------- | ---------------------------- | ----------------------------------------------------- |
| TechStackCollector         | `tech_stack`, `architecture` | `pyproject.toml` / `package.json`                     |
| BuildCmdCollector          | `build_cmd`, `test_cmd`      | `package.json` scripts                                |
| ProgressLogCollector       | `progress_log`               | Previous crew output                                  |
| GitDiffCollector           | `git_diff`, `changed_files`  | `git diff` of current branch                          |
| External plugin collectors | arbitrary                    | Via `get_context_collectors()` in entry point modules |
