# ContextInjector Plugin System

> **Status**: Planned
> **Depends on**: PLUGIN.md (existing plugin architecture)

## Problem

Context injection into agent tasks is scattered and hardcoded:

1. `FlowIssueManagement.discover_agents_md_files()` in `base.py:180-207` discovers AGENTS.md files, stores in `_agents_md_map` and `_root_agents_md`
2. Flow methods (ralph, specify) manually thread `agents_md=self._root_agents_md` and `agents_md_map=self._agents_md_map` to every crew's `.crew()` and `.kickoff(inputs=...)`
3. Crew classes (implement, plan, ralph, conversation) all accept `agents_md_map`, wire `AgentsMDLoaderTool` onto agents
4. Task YAML files use `{agents_md}` placeholder — resolved by CrewAI Jinja interpolation from `inputs=`

Other placeholders (`{task}`, `{repo}`, `{branch}`, `{build_cmd}`, `{test_cmd}`, `{file_in_repos}`, `{story}`, etc.) are all passed manually in each flow's `kickoff(inputs=...)`.

## Proposal

A **ContextInjector** is a named plugin that provides key-value pairs to be merged into crew `inputs`. A **ContextRegistry** collects all injectors and produces a merged `inputs` dict before each crew kickoff.

### Design Decisions

- **No caching** — fresh `collect()` on each crew kickoff. AGENTS.md scan is fast, allows mid-flow updates
- **Manual tool wiring** — injectors only handle the `inputs` dict. Tool injection stays in crew classes
- **Global singleton** — `ContextRegistry` follows `ModelRegistry` pattern, registered at bootstrap

### Architecture

```
                         ┌──────────────────────────┐
                         │   ContextRegistry         │
                         │   (global singleton)      │
                         │                           │
                         │  register(injector)       │
                         │  collect_all(state)→dict  │
                         └────────┬─────────────────┘
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
            ┌──────────────┐ ┌──────────┐ ┌──────────────┐
            │ AgentsMD     │ │ TechStack│ │ Custom       │
            │ Injector     │ │ Injector │ │ Injector     │
            │              │ │ (future) │ │ (future)     │
            │ keys:        │ │          │ │              │
            │  agents_md   │ │ keys:    │ │ keys:        │
            │  agents_md_  │ │  tech_   │ │  whatever    │
            │  map         │ │  stack   │ │              │
            └──────────────┘ └──────────┘ └──────────────┘
```

### Data Flow (Before vs After)

**Before** (manual threading):

```python
# In flow:
result = (
    PlanCrew()
    .crew(agents_md_map=self._agents_md_map)
    .kickoff(inputs=dict(
        task=self.state.task[:120],
        repo=self.state.repo,
        branch=self.state.branch,
        agents_md=self._root_agents_md,          # manual
        file_in_repos=self.git_operations.list_tree(),
    ))
)
```

**After** (registry-based):

```python
from modules.context_injector import ContextRegistry

injected = ContextRegistry.collect_all(self.state)
result = (
    PlanCrew()
    .crew(agents_md_map=injected.get("agents_md_map", {}))
    .kickoff(inputs=dict(
        task=self.state.task[:120],
        repo=self.state.repo,
        branch=self.state.branch,
        **injected,                              # all injectors
        file_in_repos=self.git_operations.list_tree(),
    ))
)
```

---

## Implementation Steps

### Step 1: Add `ContextInjector` protocol + `ContextRegistry`

**File:** `src/modules/context_injector.py` (NEW)

```python
"""Context injection protocol and registry.

ContextInjectors provide key-value pairs that get merged into crew kickoff
inputs. This allows modules to inject context (like AGENTS.md content,
tech stack info, build commands) into task YAML templates without manual
threading through the flow.
"""

import logging
from typing import Any, Protocol, runtime_checkable

log = logging.getLogger(__name__)


@runtime_checkable
class ContextInjector(Protocol):
    """Plugin that provides context key-values for crew task interpolation.

    Each injector declares which keys it provides (e.g., "agents_md",
    "agents_md_map"). The registry calls collect() before each crew kickoff
    and merges all results into the inputs dict.

    Modules register injectors via get_context_injectors() on their
    PolycodeModule implementation.
    """

    name: str
    keys: list[str]

    def collect(self, state: Any) -> dict[str, Any]:
        """Gather context from flow state.

        Called before each crew kickoff. Should be idempotent and fast.

        Args:
            state: The flow's state model (BaseFlowModel or subclass).

        Returns:
            Dict of key-value pairs to merge into crew inputs.
        """
        ...


class ContextRegistry:
    """Global registry of context injectors.

    Follows the same singleton pattern as ModelRegistry. Injectors are
    registered once at bootstrap, then collect_all() is called before
    each crew kickoff to build the merged inputs dict.
    """

    _injectors: dict[str, ContextInjector] = {}

    @classmethod
    def register(cls, injector: ContextInjector) -> None:
        """Register a context injector."""
        cls._injectors[injector.name] = injector
        log.info(f"💉 Registered context injector: {injector.name} (keys: {injector.keys})")

    @classmethod
    def collect_all(cls, state: Any) -> dict[str, Any]:
        """Collect context from all registered injectors.

        Args:
            state: The flow's state model.

        Returns:
            Merged dict from all injectors. Later injectors overwrite
            earlier ones on key collision (logged as warning).
        """
        result: dict[str, Any] = {}
        for injector in cls._injectors.values():
            try:
                collected = injector.collect(state)
                overlap = set(result.keys()) & set(collected.keys())
                if overlap:
                    log.warning(
                        f"⚠️ Injector '{injector.name}' overwrites keys: {overlap}"
                    )
                result.update(collected)
            except Exception as e:
                log.warning(f"⚠️ Injector '{injector.name}' collect() failed: {e}")
        return result

    @classmethod
    def get_injectors(cls) -> dict[str, ContextInjector]:
        """Return all registered injectors."""
        return dict(cls._injectors)

    @classmethod
    def reset(cls) -> None:
        """Clear registry (for testing)."""
        cls._injectors.clear()
```

### Step 2: Extend `PolycodeModule` protocol

**File:** `src/modules/protocol.py`

Add one method:

```python
@classmethod
def get_context_injectors(cls) -> list["ContextInjector"]:
    """Return context injectors provided by this module.

    Injectors are registered during bootstrap and called before
    each crew kickoff to populate task template variables.

    Returns:
        List of ContextInjector instances.
    """
    return []
```

### Step 3: Create AgentsMD module

**New directory:** `src/modules_agentsmd/`

**`src/modules_agentsmd/__init__.py`:**

```python
from .module import AgentsMDPolycodeModule

__all__ = ["AgentsMDPolycodeModule"]
```

**`src/modules_agentsmd/injector.py`:**

```python
"""Context injector for AGENTS.md file discovery."""

import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)


class AgentsMDInjector:
    """Injects AGENTS.md content into crew task templates.

    Scans the repository for AGENTS.md files and provides:
    - agents_md: root AGENTS.md content (string)
    - agents_md_map: all AGENTS.md files as {relative_path: content}
    """

    name = "agents_md"
    keys = ["agents_md", "agents_md_map"]

    def collect(self, state: Any) -> dict[str, Any]:
        repo_path = Path(state.repo) if hasattr(state, "repo") else None
        if not repo_path or not repo_path.exists():
            return {"agents_md": "", "agents_md_map": {}}

        agents_md_map: dict[str, str] = {}
        for agents_file in repo_path.rglob("AGENTS.md"):
            try:
                relative = str(agents_file.relative_to(repo_path))
                if relative.startswith("."):
                    continue
                agents_md_map[relative] = agents_file.read_text(encoding="utf-8")
                log.info(f"📕 Discovered AGENTS.md: {relative}")
            except Exception as e:
                log.error(f"Error reading {agents_file}: {e}")

        root_agents_md = agents_md_map.get("AGENTS.md", "")
        if not root_agents_md and agents_md_map:
            first_path = next(iter(agents_md_map.keys()))
            root_agents_md = agents_md_map[first_path]
            log.info(f"📕 Using {first_path} as root AGENTS.md")

        log.info(f"📕 Total AGENTS.md files discovered: {len(agents_md_map)}")
        return {
            "agents_md": root_agents_md,
            "agents_md_map": agents_md_map,
        }
```

**`src/modules_agentsmd/module.py`:**

```python
"""AgentsMD built-in module for the Polycode plugin system."""

import pluggy
from modules.context import ModuleContext
from modules.context_injector import ContextInjector
from modules.protocol import PolycodeModule


class AgentsMDPolycodeModule:
    """AgentsMD module: discovers and injects AGENTS.md content."""

    name = "agentsmd"
    version = "0.1.0"
    dependencies: list[str] = []

    @classmethod
    def on_load(cls, context: ModuleContext) -> None:
        pass

    @classmethod
    def register_hooks(cls, hook_manager: pluggy.PluginManager) -> None:
        pass

    @classmethod
    def get_context_injectors(cls) -> list[ContextInjector]:
        from .injector import AgentsMDInjector

        return [AgentsMDInjector()]
```

**`src/modules_agentsmd/loader_tool.py`:**

Move `src/tools/agents_md_loader.py` here (no logic changes):

```python
from typing import Type

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class AgentsMDLoaderInput(BaseModel):
    relative_path: str = Field(
        ...,
        description="Relative path to the AGENTS.md file to load (e.g., 'src/crews/AGENTS.md')",
    )


class AgentsMDLoaderTool(BaseTool):
    name: str = "agents_md_loader"
    description: str = ""
    args_schema: Type[BaseModel] = AgentsMDLoaderInput

    agents_md_map: dict[str, str] = Field(default_factory=dict, exclude=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.description = (
            "Load AGENTS.md content from a specific subdirectory. "
            "Use this to access project-specific CrewAI patterns and guidelines "
            "from subdirectories when needed. Available AGENTS.md files: "
            + "\n - ".join(self.agents_md_map.keys())
        )

    def _run(self, relative_path: str) -> str:
        if relative_path in self.agents_md_map:
            return f"Content of {relative_path}:\n\n{self.agents_md_map[relative_path]}"
        available = "\n".join(f"  - {path}" for path in self.agents_md_map.keys())
        return f"AGENTS.md not found at '{relative_path}'.\nAvailable AGENTS.md files:\n{available}"
```

### Step 4: Wire into bootstrap

**File:** `src/bootstrap.py`

Add after existing module registrations:

```python
from modules_agentsmd import AgentsMDPolycodeModule
module_registry.register_builtin(AgentsMDPolycodeModule)

# After load_all, register context injectors from all modules:
from modules.context_injector import ContextRegistry
for module in module_registry.modules.values():
    for injector in module.get_context_injectors():
        ContextRegistry.register(injector)
```

### Step 5: Clean up `FlowIssueManagement`

**File:** `src/flows/base.py`

Remove:

- `_agents_md_map: dict[str, str] = {}` class attribute
- `_root_agents_md: str = ""` class attribute
- `discover_agents_md_files()` method entirely
- `self.discover_agents_md_files()` call in `_setup()`

### Step 6: Update flows

**File:** `src/flows/ralph/flow.py`

```python
from modules.context_injector import ContextRegistry

# In plan() method:
injected = ContextRegistry.collect_all(self.state)
result = (
    PlanCrew()
    .crew(agents_md_map=injected.get("agents_md_map", {}))
    .kickoff(
        inputs=dict(
            task=self.state.task[:120],
            repo=self.state.repo,
            branch=self.state.branch,
            **injected,
            file_in_repos=self.git_operations.list_tree(),
        )
    )
)

# In implement() method: same pattern
injected = ContextRegistry.collect_all(self.state)
result = (
    RalphCrew()
    .crew(agents_md_map=injected.get("agents_md_map", {}))
    .kickoff(
        inputs=dict(
            task=self.state.task[:120],
            story=story.model_dump_json(),
            repo=self.state.repo,
            branch=self.state.branch,
            test_cmd=self.state.test_cmd,
            build_cmd=self.state.build_cmd,
            **injected,
            previous_errors=error_context,
        )
    )
)
```

**File:** `src/flows/specify/flow.py` — same pattern.

### Step 7: Update imports

| File                                          | Change                                                                                                                     |
| --------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `src/tools/__init__.py`                       | Change `from .agents_md_loader import AgentsMDLoaderTool` to `from modules_agentsmd.loader_tool import AgentsMDLoaderTool` |
| `src/crews/implement_crew/implement_crew.py`  | Update `from tools import AgentsMDLoaderTool` import path                                                                  |
| All crew files importing `AgentsMDLoaderTool` | Update to new location                                                                                                     |

---

## Files Changed Summary

| File                                  | Change                                               |
| ------------------------------------- | ---------------------------------------------------- |
| `src/modules/context_injector.py`     | **NEW** — ContextInjector protocol + ContextRegistry |
| `src/modules/protocol.py`             | Add `get_context_injectors()` method                 |
| `src/modules_agentsmd/__init__.py`    | **NEW** — module exports                             |
| `src/modules_agentsmd/injector.py`    | **NEW** — AgentsMDInjector                           |
| `src/modules_agentsmd/module.py`      | **NEW** — AgentsMDPolycodeModule                     |
| `src/modules_agentsmd/loader_tool.py` | **MOVED** from `src/tools/agents_md_loader.py`       |
| `src/bootstrap.py`                    | Register module + wire injectors                     |
| `src/flows/base.py`                   | Remove AGENTS.md discovery code                      |
| `src/flows/ralph/flow.py`             | Use `ContextRegistry.collect_all()`                  |
| `src/flows/specify/flow.py`           | Use `ContextRegistry.collect_all()`                  |
| `src/tools/__init__.py`               | Update import path                                   |
| `src/tools/agents_md_loader.py`       | **DELETED** (moved to modules_agentsmd)              |
| `docs/PLUGIN.md`                      | Add ContextInjector extension point section          |

---

## Test Plan

1. **Unit test `ContextRegistry`** — register, collect_all, reset, collision warning
2. **Unit test `AgentsMDInjector`** — collect from fixture directory with AGENTS.md files
3. **Unit test `AgentsMDPolycodeModule`** — protocol compliance, returns injector
4. **Integration test** — bootstrap registers injector, flow uses it to populate inputs
5. **Existing flow tests** — should pass unchanged (behavior is identical)

---

## Future Extensions

This system enables new injectors without touching flow code:

| Injector                  | Keys                                          | Source                                                    |
| ------------------------- | --------------------------------------------- | --------------------------------------------------------- |
| `TechStackInjector`       | `tech_stack`, `architecture`, `configuration` | `pyproject.toml` / `package.json` analysis                |
| `BuildCmdInjector`        | `build_cmd`, `test_cmd`                       | `package.json` scripts discovery                          |
| `ProgressLogInjector`     | `progress_log`                                | Read from previous crew output                            |
| `GitDiffInjector`         | `git_diff`, `changed_files`                   | `git diff` of current branch                              |
| External plugin injectors | arbitrary                                     | Via entry_points, registered in `get_context_injectors()` |
