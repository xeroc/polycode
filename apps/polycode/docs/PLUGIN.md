# Polycode Plugin Architecture

> **Status**: Implemented
> **Last Updated**: 2026-03-19

## Overview

Modular plugin system for Polycode enabling internal modules (`src/`) and external third-party packages to extend flow lifecycle, database schema, and application behavior.

Three pillars (+ context injection):

1. **ORM Model Registry** — auto-registration of SQLAlchemy models via `__init_subclass__`
2. **Flow Lifecycle Hooks** — `pluggy`-based hook system with **5 simplified events** (reduced from 24 phases)
3. **Module Discovery** — Python entry points for external packages, explicit registration for built-in modules
4. **Context Collectors** — modules contribute named callables that inject values into crew inputs

### Recent Changes (2026-03-19)

**Simplified Hook Architecture**: Reduced from 24 `FlowPhase` values to 5 `FlowEvent` values with label-based filtering. See [HOOK_ARCHITECTURE.md](./HOOK_ARCHITECTURE.md) for migration guide.

---

## Architecture

```
                         ┌─────────────────────┐
                         │      bootstrap()     │
                         └─────────┬───────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
            ┌──────────────┐ ┌──────────┐ ┌──────────────┐
            │ Model Imports│ │  Entry   │ │  Built-in    │
            │ (triggers    │ │  Points  │ │  Modules     │
            │  __init_sub  │ │ (ext.)   │ │  (explicit)  │
            │  _class__)   │ │          │ │              │
            └──────┬───────┘ └────┬─────┘ └──────┬───────┘
                   │              │              │
                   ▼              ▼              ▼
            ┌──────────────────────────────────────────┐
            │           ModuleRegistry                   │
            │  ┌─────────────────────────────────────┐  │
            │  │ FlowRegistry │ TaskRegistry │ CtxReg │  │
            │  └─────────────────────────────────────┘  │
            └──────────────────────────────────────────┘
                                   │
                                   ▼
            ┌──────────────────────────────────────────┐
            │           ModuleContext                   │
            │  (db_engine, hook_manager, config)       │
            └──────────────────────────────────────────┘
                                   │
                    ┌──────────────┼──────────────┐
                    ▼              ▼              ▼
             module.on_load  module.register   module.get_
                             _hooks            context_collectors
                    │              │              │
                    ▼              ▼              ▼
            ┌──────────────────────────────────────────┐
            │         pluggy PluginManager              │
            │         (hook dispatch)                   │
            └──────────────────────────────────────────┘
```

---

## 1. File Structure

```
src/
├── persistence/
│   ├── __init__.py
│   ├── postgres.py          # Core models (Requests, Payments, FlowState, etc.)
│   └── registry.py          # ModelRegistry, RegisteredBase
├── modules/
│   ├── __init__.py
│   ├── protocol.py          # PolycodeModule protocol
│   ├── hooks.py             # FlowEvent enum, hook specifications
│   ├── context.py           # ModuleContext dataclass
│   ├── registry.py          # ModuleRegistry (discovery + loading)
│   └── tasks.py            # Celery task collection
├── flows/
│   ├── base.py             # FlowIssueManagement, KickoffIssue base classes
│   ├── protocol.py          # FlowDef dataclass
│   ├── registry.py          # FlowRegistry class
│   └── ralph/              # Ralph flow implementation
├── crews/
│   ├── base.py             # PolycodeCrewMixin (auto-emit CREW_FINISHED)
│   ├── plan_crew/          # Planning crew
│   ├── implement_crew/      # Implementation crew
│   ├── review_crew/        # Review crew
│   └── verify_crew/        # Verification crew
├── project_manager/         # GitHub integration
│   ├── github.py           # GitHub API client
│   └── types.py            # ProjectConfig, StatusMapping
├── github_app/              # FastAPI webhook server
│   ├── app.py              # FastAPI application
│   └── webhook_handler.py  # Webhook processing
├── celery_tasks/            # Celery task definitions
│   ├── flow_orchestration.py
│   ├── agent_execution.py
│   ├── webhook_tasks.py
│   └── utility_tasks.py
├── gitcore/                # Git operations
│   └── gitops.py          # Git operations
├── cli/                    # Typer-based CLI
│   ├── main.py             # Main entry point
│   ├── project.py          # Project management commands
│   ├── flow.py            # Flow execution commands
│   ├── server.py           # Webhook server commands
│   ├── worker.py           # Celery worker commands
│   └── db.py              # Database commands
├── retro/                  # Retrospectives module
│   ├── persistence.py
│   └── hooks.py
└── bootstrap.py             # Plugin initialization
```

---

## 2. ORM Model Registry

### `src/persistence/registry.py`

```python
"""SQLAlchemy model registry with auto-registration via __init_subclass__."""

import logging
from typing import Type

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

log = logging.getLogger(__name__)


METADATA = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s",
    }
)


class ModelRegistry:
    """Central registry for ORM models from all modules."""

    _models: dict[str, Type[DeclarativeBase]] = {}
    _modules: set[str] = set()

    @classmethod
    def register_model(cls, model: Type[DeclarativeBase], module_name: str) -> None:
        """Register a single model under its module name."""
        key = f"{module_name}.{model.__tablename__}"
        cls._models[key] = model

    @classmethod
    def register_module(cls, module_name: str) -> None:
        """Mark a module as having been processed."""
        cls._modules.add(module_name)

    @classmethod
    def is_registered(cls, module_name: str) -> bool:
        return module_name in cls._modules

    @classmethod
    def create_all(cls, engine) -> None:
        """Create all registered tables in one pass."""
        METADATA.create_all(bind=engine)
        log.info(
            f"📊 Created {len(cls._models)} tables "
            f"from {len(cls._modules)} modules"
        )

    @classmethod
    def get_models_for_module(cls, module_name: str) -> list[Type[DeclarativeBase]]:
        """Return all models belonging to a module."""
        prefix = f"{module_name}."
        return [
            m for key, m in cls._models.items()
            if key.startswith(prefix)
        ]

    @classmethod
    def all_models(cls) -> dict[str, Type[DeclarativeBase]]:
        """Return all registered models as {module.table: model}."""
        return dict(cls._models)

    @classmethod
    def reset(cls) -> None:
        """Clear registry (for testing)."""
        cls._models.clear()
        cls._modules.clear()


class RegisteredBase(DeclarativeBase):
    """Base class for ORM models with auto-registration.

    All models across all modules inherit from this. Each model must
    declare __module_name__ to identify its owning module.

    Usage:

        class MyModel(RegisteredBase):
            __module_name__ = "my_module"
            __tablename__ = "my_table"

            id: Mapped[int] = mapped_column(primary_key=True)

    The __init_subclass__ hook automatically registers the model with
    ModelRegistry when the class is defined (at import time).

    If __module_name__ is omitted, the registry attempts to infer it from
    the class's __module__ attribute (e.g., 'src.retro.persistence' -> 'retro').
    """

    metadata = METADATA
    __module_name__: str

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)

        if getattr(cls, "__abstract__", False):
            return

        module_name = getattr(cls, "__module_name__", None)
        if not module_name:
            parts = cls.__module__.split(".")
            if len(parts) >= 2 and parts[0] == "src":
                module_name = parts[1]

        if module_name:
            ModelRegistry.register_model(cls, module_name)
            ModelRegistry.register_module(module_name)
            log.debug(f"📊 Auto-registered: {module_name}.{cls.__tablename__}")
        else:
            log.warning(
                f"⚠️ {cls.__name__} has no __module_name__ and cannot "
                f"be inferred from __module__={cls.__module__!r}"
            )
```

### Migration: Existing Models

**`src/persistence/postgres.py`** — minimal changes:

```python
# BEFORE:
class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""

class Requests(Base):
    __tablename__ = "requests"
    ...

# AFTER:
from persistence.registry import RegisteredBase

class Base(RegisteredBase):
    """SQLAlchemy base with auto-registration."""
    __abstract__ = True

class Requests(Base):
    __module_name__ = "core"
    __tablename__ = "requests"
    ...
```

**`src/retro/persistence.py`** — minimal changes:

```python
# BEFORE:
class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""

class RetroModel(Base):
    __tablename__ = "retrospectives"
    ...

# AFTER:
from persistence.registry import RegisteredBase

class RetroModel(RegisteredBase):
    __module_name__ = "retro"
    __tablename__ = "retrospectives"
    ...
```

All existing model code, queries, session usage stays identical. The only change is inheritance and adding `__module_name__`.

---

## 3. Flow Lifecycle Hooks

### `src/modules/hooks.py`

```python
"""Flow lifecycle hook specifications.

Uses pluggy (already a dependency of crewai via pytest) for hook management.

Simplified event-based system with 5 events instead of 24 phases.
Modules register hook implementations via @hookimpl decorator.
"""

from enum import StrEnum

import pluggy

POLYCODE_NS = "polycode"

hookspec = pluggy.HookspecMarker(POLYCODE_NS)
hookimpl = pluggy.HookimplMarker(POLYCODE_NS)


class FlowEvent(StrEnum):
    """Flow lifecycle events.

    Simplified event-based hook system. Plugins filter by event + label.

    Labels provide context:
    - CREW_FINISHED: "plan", "implement", "review"
    - STORY_COMPLETED: story.id or story.title
    - FLOW_STARTED/FINISHED: flow name (e.g., "ralph")

    Crew-level lifecycle (@before_kickoff, @after_kickoff) is handled by
    PolycodeCrew base class which emits CREW_FINISHED events.
    """

    FLOW_STARTED = "flow_started"
    FLOW_FINISHED = "flow_finished"
    FLOW_ERROR = "flow_error"

    CREW_FINISHED = "crew_finished"
    STORY_COMPLETED = "story_completed"


class FlowHookSpec:
    """Hook specifications for flow lifecycle events.

    Implementations use the @hookimpl decorator from modules/hooks.py.

    Example:

        from modules.hooks import FlowEvent, hookimpl

        class MyHooks:
            @hookimpl
            def on_flow_event(self, event, flow_id, state, result=None, label=""):
                if event == FlowEvent.CREW_FINISHED and label == "plan":
                    print(f"Planning crew finished in flow {flow_id}")

                if event == FlowEvent.STORY_COMPLETED:
                    # Commit and push changes
                    self.git_ops.commit_and_push(state, result)

                if event == FlowEvent.FLOW_FINISHED:
                    # Create PR, merge, cleanup
                    self.finalize_flow(flow_id, state)
    """

    @hookspec
    def on_flow_event(
        self,
        event: FlowEvent,
        flow_id: str,
        state: object,
        result: object | None = None,
        label: str = "",
    ) -> None:
        """Called at each flow lifecycle event.

        Args:
            event: Which event is firing (FLOW_STARTED, CREW_FINISHED, etc.).
            flow_id: Unique flow identifier.
            state: The flow's state model (read-only reference).
            result: Event-specific result (e.g., Story object, crew output).
            label: Context label (e.g., "plan", "implement", "ralph").
        """
        ...


def get_plugin_manager() -> pluggy.PluginManager:
    """Create and configure the plugin manager with hook specs."""
    pm = pluggy.PluginManager(POLYCODE_NS)
    pm.add_hookspecs(FlowHookSpec)
    return pm
```

### Hook Slot Points in `flowbase.py`

The following table defines every hook insertion point. Each `_emit()` call
invokes `pm.hook.on_flow_phase(phase, ...)`.

| Phase                  | Method                      | Position                           | State Available                | Result                  |
| ---------------------- | --------------------------- | ---------------------------------- | ------------------------------ | ----------------------- |
| `PRE_SETUP`            | `_setup()`                  | Before `_prepare_work_tree()`      | repo, branch, task             | None                    |
| `POST_SETUP`           | `_setup()`                  | After `ensure_request_exists()`    | + issue_id                     | None                    |
| `PRE_PLAN`             | `setup()` in FeatureDevFlow | Before `PlanCrew.kickoff()`        | Full state                     | None                    |
| `POST_PLAN`            | `setup()` in FeatureDevFlow | After stories populated            | + stories, build_cmd, test_cmd | PlanOutput              |
| `PRE_IMPLEMENT`        | `implement_story()`         | Before story loop                  | + stories                      | None                    |
| `POST_IMPLEMENT_STORY` | `implement_story()`         | After each single story            | + completed_stories            | ImplementOutput         |
| `POST_IMPLEMENT`       | `implement_story()`         | After all stories done             | + completed_stories            | None                    |
| `PRE_COMMIT`           | `_commit_changes()`         | Before `repo.index.commit()`       | Full state                     | None                    |
| `POST_COMMIT`          | `_commit_changes()`         | After commit                       | Full state                     | commit (git.Commit)     |
| `PRE_PUSH`             | `_push_repo()`              | Before `repo.git.push()`           | Full state                     | None                    |
| `POST_PUSH`            | `_push_repo()`              | After push                         | Full state                     | None                    |
| `PRE_PR`               | `_create_pr()`              | Before `github_repo.create_pull()` | Full state                     | None                    |
| `POST_PR`              | `_create_pr()`              | After PR created                   | + pr_number, pr_url            | pr (github.PullRequest) |
| `PRE_REVIEW`           | `review()`                  | Before `ReviewCrew.kickoff()`      | + diff                         | None                    |
| `POST_REVIEW`          | `review()`                  | After review                       | + review_status                | ReviewOutput            |
| `PRE_MERGE`            | `_merge_branch()`           | Before merge check                 | + pr_number                    | None                    |
| `POST_MERGE`           | `_merge_branch()`           | After merge                        | + pr_number                    | None                    |
| `PRE_CLEANUP`          | `_cleanup_worktree()`       | Before cleanup                     | Full state                     | None                    |
| `POST_CLEANUP`         | `_cleanup_worktree()`       | After worktree removed             | Full state                     | None                    |
| `ON_COMPLETE`          | `finish()`                  | Very end, after cleanup            | Full state                     | None                    |
| `ON_ERROR`             | Any                         | On unhandled exception             | State at time of error         | Exception               |

### Implementation Pattern in `flowbase.py`

```python
# At class level:
class FlowIssueManagement(Flow[T]):
    _pm: pluggy.PluginManager | None = None

    @classmethod
    def use_plugin_manager(cls, pm: pluggy.PluginManager) -> None:
        """Inject plugin manager for all flow instances."""
        cls._pm = pm

    def _emit(self, phase: FlowPhase, result: object | None = None) -> None:
        """Emit a hook event. Safe to call even if no pm configured."""
        if not self._pm:
            return
        try:
            self._pm.hook.on_flow_phase(
                phase=phase,
                flow_id=str(getattr(self.state, "id", "")),
                state=self.state,
                result=result,
            )
        except Exception as e:
            log.warning(f"⚠️ Hook error in {phase}: {e}")

    def _should_skip(self, phase: FlowPhase) -> bool:
        """Check if any module wants to skip this phase."""
        if not self._pm:
            return False
        return bool(
            self._pm.hook.should_skip_phase(
                phase=phase,
                flow_id=str(getattr(self.state, "id", "")),
                state=self.state,
            )
        )

# In each method:
    def _setup(self):
        self._emit(FlowPhase.PRE_SETUP)
        self._prepare_work_tree()
        if not self.state.project_config:
            raise ValueError("project_config required!")
        try:
            ensure_request_exists(SessionLocal, self.state.issue_id, self.state.task)
            log.info(f"🏹 Ensured request exists for issue #{self.state.issue_id}")
        except Exception as e:
            log.error(f"🚨 Failed to ensure request exists: {e}")
        self._emit(FlowPhase.POST_SETUP)

    def _commit_changes(self, title: str, body="", footer=""):
        self._emit(FlowPhase.PRE_COMMIT)
        repo = git.Repo(self.state.repo)
        repo.git.add(A=True)
        commit_message = f"{title}\n\n{body}\n\n{footer}"
        commit = repo.index.commit(commit_message)
        log.info(f"🏹 Committed changes: {commit_message.split(chr(10))[0]} ...")
        self._emit(FlowPhase.POST_COMMIT, result=commit)
        return commit
```

---

## 4. Module Protocol

### `src/modules/protocol.py`

```python
"""Protocol for polycode modules."""

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from flows.protocol import FlowDef
    from modules.context import ModuleContext

if TYPE_CHECKING:
    import pluggy


class PolycodeModule(Protocol):
    """Protocol that all modules (built-in and external) must satisfy.

    A module is a class or object with:

    - name (str): Unique module identifier.
    - version (str): Semantic version.
    - dependencies (list[str]): Names of modules that must load first.

    Methods are classmethods so modules can be defined as classes
    without instantiation.

    Built-in modules are registered explicitly in bootstrap().
    External modules are discovered via entry_points["polycode.modules"].
    """

    name: str
    version: str
    dependencies: list[str]

    @classmethod
    def on_load(cls, context: "ModuleContext") -> None:
        """Called after all models are registered and tables created.

        Initialize module resources (DB connections, caches, etc.).
        """
        ...

    @classmethod
    def register_hooks(cls, hook_manager: "pluggy.PluginManager") -> None:
        """Register hook implementations.

        Called after on_load(). Modules that don't use hooks can no-op.
        """
        ...

    @classmethod
    def get_models(cls) -> list[type]:
        """Return ORM model classes for this module.

        Optional — models are auto-registered via RegisteredBase.
        This method is for explicit listing when needed (docs, introspection).
        """
        return []

    @classmethod
    def get_tasks(cls) -> list[dict[str, Any]]:
        """Return Celery task definitions from this module."""
        return []

    @classmethod
    def get_flows(cls) -> list["FlowDef"]:
        """Return flow definitions provided by this module."""
        return []

    @classmethod
    def get_context_collectors(cls) -> list[tuple[str, Any]]:
        """Return context collectors as (name, callable) pairs.

        Each callable takes a flow state and returns dict[str, Any]
        to merge into crew kickoff inputs. Called before each crew kickoff.

        Returns:
            List of (name, collect_fn) tuples.
        """
        return []
```

### `src/modules/context.py`

```python
"""Context object passed to modules during initialization."""

from dataclasses import dataclass, field
from typing import Any

import pluggy
from sqlalchemy import Engine


@dataclass
class ModuleContext:
    """Shared context for module initialization.

    Passed to module.on_load() during bootstrap.
    """

    db_engine: Engine
    db_url: str
    hook_manager: pluggy.PluginManager
    config: dict[str, Any] = field(default_factory=dict)

    def get_module_config(self, module_name: str) -> dict[str, Any]:
        """Get config dict for a specific module.

        Config is loaded from environment or config file.
        Module-specific config lives under config[module_name].
        """
        return self.config.get(module_name, {})
```

---

## 5. Module Registry (Discovery + Loading)

### `src/modules/registry.py`

````python
"""Central registry for all resources (modules, flows, tasks, context)."""

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import pluggy

if TYPE_CHECKING:
    from modules.context import ModuleContext

from modules.hooks import get_plugin_manager
from modules.protocol import PolycodeModule

log = logging.getLogger(__name__)


class FlowRegistry:
    """Registry for flow definitions contributed by modules."""
    # ... (see full source)


class TaskRegistry:
    """Registry for Celery tasks contributed by modules."""
    # ... (see full source)


class ContextRegistry:
    """Registry for context collectors contributed by modules.

    Modules contribute named callables via get_context_collectors().
    Each callable takes a flow state and returns a dict to merge into
    crew kickoff inputs.
    """

    def __init__(self) -> None:
        self._collectors: dict[str, Callable[[Any], dict[str, Any]]] = {}

    def register(self, name: str, collect_fn: Callable[[Any], dict[str, Any]]) -> None:
        """Register a named context collector."""
        if name in self._collectors:
            log.warning(f"⚠️ Context collector '{name}' already registered, overwriting")
        self._collectors[name] = collect_fn
        log.info(f"💉 Registered context collector: {name}")

    def collect_all(self, state: Any) -> dict[str, Any]:
        """Run all collectors and merge results.

        Failures are logged and skipped. Key collisions log warnings.
        """
        result: dict[str, Any] = {}
        for name, fn in self._collectors.items():
            try:
                collected = fn(state)
                overlap = set(result.keys()) & set(collected.keys())
                if overlap:
                    log.warning(f"⚠️ Collector '{name}' overwrites keys: {overlap}")
                result.update(collected)
            except Exception as e:
                log.warning(f"⚠️ Collector '{name}' failed: {e}")
        return result

    def collect_from_modules(self, modules: dict[str, Any]) -> int:
        """Collect context collectors from all modules.

        Iterates modules, calls get_context_collectors() if present,
        registers returned (name, callable) tuples.

        Returns:
            Number of collectors registered.
        """
        count = 0
        for module_name, module in modules.items():
            if not hasattr(module, "get_context_collectors"):
                continue
            try:
                collectors = module.get_context_collectors()
                for name, fn in collectors:
                    self.register(name, fn)
                    count += 1
            except Exception as e:
                log.error(
                    f"🚨 Module '{module_name}' get_context_collectors() failed: {e}"
                )
        log.info(f"💉 Collected {count} context collectors from modules")
        return count


class ModuleRegistry:
    """Central registry for modules, flows, tasks, and context."""

    def __init__(self) -> None:
        self._modules: dict[str, PolycodeModule] = {}
        self._pm = get_plugin_manager()

        self._flow_registry = FlowRegistry()
        self._task_registry = TaskRegistry()
        self._context_registry = ContextRegistry()

    @property
    def pm(self) -> pluggy.PluginManager:
        """The shared plugin manager."""
        return self._pm

    @property
    def modules(self) -> dict[str, PolycodeModule]:
        """All registered modules."""
        return dict(self._modules)

    @property
    def flow_registry(self) -> FlowRegistry:
        return self._flow_registry

    @property
    def task_registry(self) -> TaskRegistry:
        return self._task_registry

    @property
    def context_registry(self) -> ContextRegistry:
        return self._context_registry

    # ... discover(), register_builtin(), load_all(), _topological_sort()
    # ... (see full source)
```, get_plugin_manager
from modules.protocol import PolycodeModule

log = logging.getLogger(__name__)


class ModuleRegistry:
    """Discovers external modules via entry points and manages loading."""

    def __init__(self) -> None:
        self._modules: dict[str, PolycodeModule] = {}
        self._pm = get_plugin_manager()

    @property
    def pm(self) -> pluggy.PluginManager:
        """The shared plugin manager."""
        return self._pm

    @property
    def modules(self) -> dict[str, PolycodeModule]:
        """All registered modules."""
        return dict(self._modules)

    def discover(self) -> None:
        """Scan entry points for external polycode modules.

        Looks for entry_points under group "polycode.modules".
        Each entry point should resolve to a class or object
        satisfying the PolycodeModule protocol.
        """
        import importlib.metadata

        group = "polycode.modules"
        try:
            eps = importlib.metadata.entry_points(group=group)
        except AttributeError:
            eps = importlib.metadata.entry_points().get(group, [])

        for ep in eps:
            try:
                module_cls = ep.load()
                if not hasattr(module_cls, "name"):
                    log.warning(
                        f"⚠️ Entry point '{ep.name}' missing 'name' attribute, skipping"
                    )
                    continue
                self._modules[ep.name] = module_cls
                log.info(f"📦 Discovered external module: {ep.name} (v{getattr(module_cls, 'version', '?')})")
            except Exception as e:
                log.error(f"🚨 Failed to load module '{ep.name}': {e}")

    def register_builtin(self, module: PolycodeModule) -> None:
        """Register a built-in module explicitly.

        Args:
            module: A class or object satisfying PolycodeModule protocol.
        """
        name = module.name
        if name in self._modules:
            log.warning(f"⚠️ Module '{name}' already registered, overwriting")
        self._modules[name] = module
        log.info(f"📦 Registered built-in module: {name}")

    def load_all(self, context: "ModuleContext") -> None:
        """Load all modules in dependency order.

        1. Topological sort based on dependencies.
        2. Call on_load() for each module.
        3. Call register_hooks() for each module.

        Raises:
            RuntimeError: If circular dependency detected.
        """
        sorted_names = self._topological_sort()

        for name in sorted_names:
            module = self._modules[name]
            log.info(f"🔧 Loading module: {name}")

            try:
                module.on_load(context)
            except Exception as e:
                log.error(f"🚨 Module '{name}' on_load() failed: {e}")
                raise

            try:
                module.register_hooks(self._pm)
            except Exception as e:
                log.error(f"🚨 Module '{name}' register_hooks() failed: {e}")
                raise

            log.info(f"✅ Module loaded: {name}")

    def _topological_sort(self) -> list[str]:
        """Sort modules by dependencies using Kahn's algorithm.

        Returns:
            List of module names in dependency order.

        Raises:
            RuntimeError: If circular dependency detected.
        """
        in_degree: dict[str, int] = {name: 0 for name in self._modules}
        dependents: dict[str, list[str]] = {name: [] for name in self._modules}

        for name, module in self._modules.items():
            for dep in getattr(module, "dependencies", []):
                if dep not in self._modules:
                    log.warning(
                        f"⚠️ Module '{name}' depends on '{dep}' which is not registered"
                    )
                    continue
                dependents[dep].append(name)
                in_degree[name] += 1

        queue = [name for name, deg in in_degree.items() if deg == 0]
        result: list[str] = []

        while queue:
            node = queue.pop(0)
            result.append(node)
            for dependent in dependents[node]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(result) != len(self._modules):
            remaining = set(self._modules) - set(result)
            raise RuntimeError(f"Circular dependency detected among modules: {remaining}")

        return result
````

---

## 6. Bootstrap

### `src/bootstrap.py`

```python
"""Application bootstrap — single entry point for initialization.

Call bootstrap() once at application startup (FastAPI lifespan, CLI, etc.).
After bootstrap, modules are loaded and hooks are active.
"""

import logging
import os
from typing import Any

from sqlalchemy import create_engine

from modules.context import ModuleContext
from modules.registry import ModuleRegistry
from persistence.registry import METADATA, ModelRegistry

log = logging.getLogger(__name__)


def bootstrap(config: dict[str, Any] | None = None) -> ModuleContext:
    """Initialize the full polycode runtime.

    Steps:
        1. Create SQLAlchemy engine
        2. Import all model modules (triggers __init_subclass__ registration)
        3. Discover external modules via entry points
        4. Register built-in modules
        5. Create all database tables
        6. Load all modules (on_load + register_hooks)

    Args:
        config: Optional config dict. Keys:
            - db_url: str (default: DATABASE_URL env var)
            - modules: dict of module_name -> module_config dicts

    Returns:
        ModuleContext with engine, hook manager, and config.

    Example:

        from bootstrap import bootstrap
        context = bootstrap()
        # Now all modules are loaded, hooks are active, tables exist
    """
    cfg = config or {}

    # 1. Database
    db_url = cfg.get("db_url") or os.getenv(
        "DATABASE_URL",
        "postgresql://user:password@localhost:5432/polycode",
    )
    engine = create_engine(db_url)

    # 2. Import all model modules to trigger auto-registration
    # Core models
    import persistence.postgres  # noqa: F401
    # Built-in module models
    import retro.persistence  # noqa: F401
    # Add new modules here as they are created

    # 3. Discover external modules
    module_registry = ModuleRegistry()
    module_registry.discover()

    # 4. Register built-in modules
    from retro import RetroPolycodeModule
    module_registry.register_builtin(RetroPolycodeModule)
    # Add new built-in modules here

    # 5. Create all tables
    ModelRegistry.create_all(engine)

    # 6. Build context and load modules
    context = ModuleContext(
        db_engine=engine,
        db_url=db_url,
        hook_manager=module_registry.pm,
        config=cfg.get("modules", {}),
    )
    module_registry.load_all(context)

    # 7. Wire plugin manager into flow and crew base classes
    from crews.base import PolycodeCrewMixin
    from flows.base import FlowIssueManagement
    FlowIssueManagement.use_plugin_manager(module_registry.pm)
    PolycodeCrewMixin.use_plugin_manager(module_registry.pm)

    module_count = len(module_registry.modules)
    model_count = len(ModelRegistry.all_models())
    log.info(f"🚀 Bootstrap complete: {module_count} modules, {model_count} tables")

    return context
```

---

## 7. Built-in Retro Module Changes

### `src/retro/__init__.py` — add module class

Add the following class (don't remove existing code):

```python
from modules.protocol import PolycodeModule
from modules.context import ModuleContext
import pluggy


class RetroPolycodeModule:
    """Retro module: built-in but using the plugin protocol."""

    name = "retro"
    version = "0.1.0"
    dependencies: list[str] = []

    @classmethod
    def on_load(cls, context: ModuleContext) -> None:
        """Initialize retro database connection."""
        from retro.persistence import init_db
        init_db(context.db_url)

    @classmethod
    def register_hooks(cls, hook_manager: pluggy.PluginManager) -> None:
        """Register retrospective hooks."""
        from retro.hooks import RetroHooks
        hook_manager.register(RetroHooks())

    @classmethod
    def get_models(cls) -> list[type]:
        from retro.persistence import RetroModel
        return [RetroModel]
```

### `src/retro/hooks.py` — new file

```python
"""Hook implementations for the retro module."""

import logging

from modules.hooks import FlowPhase, hookimpl

log = logging.getLogger(__name__)


class RetroHooks:
    """Lifecycle hooks for retrospective generation."""

    @hookimpl
    def on_flow_complete(self, flow_id: str, state: object) -> None:
        """Generate success retrospective when flow completes."""
        from retro.analyzer import generate_retro
        generate_retro(flow_id=flow_id, state=state, retro_type="success")

    @hookimpl
    def on_flow_error(
        self, flow_id: str, state: object, error: Exception
    ) -> bool | None:
        """Generate failure retrospective on error."""
        from retro.analyzer import generate_retro
        generate_retro(
            flow_id=flow_id,
            state=state,
            retro_type="failure",
            error=str(error),
        )
        return None
```

### `src/retro/persistence.py` — ORM changes

Replace:

```python
class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""
```

With:

```python
from persistence.registry import RegisteredBase
```

And change:

```python
class RetroModel(Base):
```

To:

```python
class RetroModel(RegisteredBase):
    __module_name__ = "retro"
```

Remove the module-level `Base` class entirely.

---

## 8. External Module Template

### Package structure

```
polycode-<name>/
├── pyproject.toml
└── src/
    └── polycode_<name>/
        ├── __init__.py       # exports MODULE
        ├── module.py          # PolycodeModule implementation
        ├── persistence.py     # ORM models (extend RegisteredBase)
        ├── hooks.py           # @hookimpl implementations
        └── types.py           # Pydantic types (optional)
```

### `pyproject.toml`

```toml
[project]
name = "polycode-<name>"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = ["polycode"]

[project.entry-points."polycode.modules"]
<name> = "polycode_<name>.module:<Name>Module"
```

### `module.py`

```python
import pluggy
from flows.protocol import FlowDef
from modules.protocol import PolycodeModule
from modules.context import ModuleContext

class NameModule:
    """Module description."""

    name = "<name>"
    version = "0.1.0"
    dependencies = []  # e.g., ["retro"] if this module needs retro loaded first

    @classmethod
    def on_load(cls, context: ModuleContext) -> None:
        """Initialize."""
        pass

    @classmethod
    def register_hooks(cls, hook_manager: pluggy.PluginManager) -> None:
        """Register hooks."""
        from .hooks import NameHooks
        hook_manager.register(NameHooks())

    @classmethod
    def get_flows(cls) -> list[FlowDef]:
        """Return flow definitions provided by this module."""
        return []

    @classmethod
    def get_celery_tasks(cls) -> list[dict[str, Any]]:
        """Return Celery task definitions provided by this module."""
        return []
```

### `persistence.py`

```python
from persistence.registry import RegisteredBase
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Integer

class MyModel(RegisteredBase):
    __module_name__ = "<name>"
    __tablename__ = "<name>_things"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
```

### `hooks.py`

```python
import logging
from modules.hooks import FlowEvent, hookimpl

log = logging.getLogger(__name__)

class NameHooks:
    @hookimpl
    def on_flow_event(
        self,
        event: FlowEvent,
        flow_id: str,
        state: object,
        result: object | None = None,
        label: str = "",
    ) -> None:
        if event == FlowEvent.STORY_COMPLETED:
            # Handle story completion
            log.info(f"Story completed: {label}")
        if event == FlowEvent.FLOW_FINISHED:
            # Handle flow completion
            log.info(f"Flow finished: {flow_id}")
```

---

## 9. Hook Implementation Reference

### pluggy `@hookimpl` Options

```python
@hookimpl
def basic(self, phase, flow_id, state):
    """Standard hook — always called."""
    pass

@hookimpl(hookwrapper=True)
def wrapping(self, phase, flow_id, state):
    """Wrapper hook — can inspect/replace result.

    Must use yield pattern:
        outcome = yield
        # outcome.get_result() gives the result
    """
    outcome = yield
    print(f"Result was: {outcome.get_result()}")

@hookimpl(tryfirst=True)
def early(self, phase, flow_id, state):
    """Runs before other hooks (no guaranteed order otherwise)."""
    pass

@hookimpl(trylast=True)
def late(self, phase, flow_id, state):
    """Runs after other hooks."""
    pass

@hookimpl(specname="on_flow_phase")
def custom_name(self, phase, flow_id, state):
    """Hook a different spec from a method with any name."""
    pass
```

### Hook Execution Order

When multiple modules hook into the same phase, execution order is:

1. `tryfirst=True` implementations (in registration order)
2. Regular implementations (in registration order)
3. `trylast=True` implementations (in registration order)
4. `hookwrapper=True` implementations wrap around all others

For `firstresult=True` specs (like `should_skip_phase`), the first non-None
return wins and remaining hooks are skipped.

---

## 10. Configuration

### Environment-based config (recommended for v1)

Module config is passed via `ModuleContext.config`:

```python
context = bootstrap(config={
    "modules": {
        "retro": {
            "enabled": True,
            "max_failures": 100,
        },
        "billing": {
            "api_key": "...",
        },
    }
})
```

Modules access their config:

```python
@classmethod
def on_load(cls, context: ModuleContext) -> None:
    cfg = context.get_module_config("my_module")
    api_key = cfg.get("api_key")
```

### Future: Config file

```yaml
# polycode.yaml
modules:
  retro:
    enabled: true
    max_failures: 100
  billing:
    api_key: ${BILLING_API_KEY} # env var interpolation
```

---

## 11. Testing Strategy

### Unit tests for registry

```python
def test_model_auto_registration():
    """Model classes auto-register when defined."""
    ModelRegistry.reset()

    class TestModel(RegisteredBase):
        __module_name__ = "test"
        __tablename__ = "test_table"
        id: Mapped[int] = mapped_column(primary_key=True)

    assert "test.test_table" in ModelRegistry.all_models()
    assert ModelRegistry.is_registered("test")


def test_module_name_inference():
    """Module name inferred from __module__ when __module_name__ missing."""
    ModelRegistry.reset()

    class FakeModel(RegisteredBase):
        # No __module_name__ — will be inferred from __module__
        __tablename__ = "fake_table"
        id: Mapped[int] = mapped_column(primary_key=True)

    # __module__ would be 'tests.test_registry', so inferred as 'tests'
    # This is the fallback behavior
```

### Unit tests for hooks

```python
def test_hook_emission():
    """_emit calls registered hooks."""
    pm = get_plugin_manager()

    calls = []

    class TestHooks:
        @hookimpl
        def on_flow_phase(self, phase, flow_id, state, result=None):
            calls.append(phase)

    pm.register(TestHooks())
    FlowIssueManagement.use_plugin_manager(pm)

    flow = FlowIssueManagement.__new__(FlowIssueManagement)
    flow._emit(FlowPhase.PRE_COMMIT)

    assert FlowPhase.PRE_COMMIT in calls


def test_should_skip_phase():
    """should_skip_phase with firstresult stops early."""
    pm = get_plugin_manager()

    class SkipHooks:
        @hookimpl
        def should_skip_phase(self, phase, flow_id, state):
            if phase == FlowPhase.PRE_TEST:
                return True
            return None

    pm.register(SkipHooks())
    assert pm.hook.should_skip_phase(
        phase=FlowPhase.PRE_TEST, flow_id="test", state={}
    ) is True
```

### Unit tests for module loading

```python
def test_builtin_module_registration():
    """Built-in modules register with ModuleRegistry."""
    registry = ModuleRegistry()
    registry.register_builtin(RetroPolycodeModule)

    assert "retro" in registry.modules


def test_topological_sort():
    """Modules load in dependency order."""
    registry = ModuleRegistry()

    class ModA:
        name = "a"
        dependencies = ["b"]

    class ModB:
        name = "b"
        dependencies = []

    registry.register_builtin(ModA)
    registry.register_builtin(ModB)

    order = registry._topological_sort()
    assert order.index("b") < order.index("a")


def test_circular_dependency_raises():
    """Circular dependencies raise RuntimeError."""
    registry = ModuleRegistry()

    class ModX:
        name = "x"
        dependencies = ["y"]

    class ModY:
        name = "y"
        dependencies = ["x"]

    registry.register_builtin(ModX)
    registry.register_builtin(ModY)

    with pytest.raises(RuntimeError, match="Circular dependency"):
        registry._topological_sort()
```

---

## 12. Module Development Checklist

Implementation order for creating a new module (each step is independently testable):

- [ ] **1. Create persistence models** — Create `src/my_module/persistence.py` with `RegisteredBase` models
- [ ] **2. Create hooks** — Create `src/my_module/hooks.py` with `@hookimpl` methods
- [ ] **3. Create module class** — Create `src/my_module/module.py` implementing `PolycodeModule`
- [ ] **4. Register in bootstrap** — Add `module_registry.register_builtin(MyModule)` to `bootstrap.py`
- [ ] **5. Unit tests** — Write tests for models, hooks, and module loading
- [ ] **6. Integration test** — Test that module loads correctly and hooks fire

## 13. Dependencies

| Package      | Version  | Notes                                                    |
| ------------ | -------- | -------------------------------------------------------- |
| `pluggy`     | >=1.5    | Already transitive via `crewai` → `pytest`. Hook system. |
| `sqlalchemy` | >=2.0    | Already a dependency. ORM + metadata.                    |
| `pydantic`   | >=2.0    | Already a dependency. Module protocol, state models.     |
| `crewai`     | >=1.10.0 | Flow and crew orchestration.                             |
| `celery`     | >=5.4.0  | Background task processing.                              |

No new dependencies required for modules.
