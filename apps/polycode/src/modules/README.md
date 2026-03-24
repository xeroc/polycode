# Polycode Modules — Plugin System Documentation

This directory implements a sophisticated plugin architecture for Polycode, enabling dynamic module discovery, lifecycle management, and extensibility without modifying core application code.

---

## 📋 Overview

The `modules/` directory provides a **plugin subsystem** that allows Polycode to dynamically load and manage external modules. Think of it as a plugin system similar to WordPress plugins or Rails gems, but with CrewAI flow orchestration integration.

**Key Capabilities:**

- ✅ Dynamic module discovery via entry points
- ✅ Dependency resolution and topological sorting
- ✅ Shared context injection (database, config, hooks)
- ✅ Flow event system (git, PRs, cleanup notifications)
- ✅ Communication channel registry (Slack, GitHub, Redis, etc.)
- ✅ Celery task registration from modules
- ✅ Extensibility through `PolycodeModule` protocol

---

## 🏗️ Architecture

```
modules/
├── __init__.py          # Module entry point & exports
├── channels.py         # Notification channel system
├── context.py          # Shared context for modules
├── hooks.py            # Flow event specifications & decorators
├── protocol.py         # Module contract/interface
├── registry.py         # Module discovery & lifecycle
├── tasks.py            # Celery task registration
└── README.md           # This file
```

### Component Relationships

```
                    ┌─────────────────────────────────────────────┐
                    │  External Modules (GitHub, local, etc.) │
                    └─────────────────────┐      │
                                   ▼
                                   │
                    ┌───────────────────────────────────────────────┐
                    │         ModuleRegistry (registry.py)       │
                    │              │          │
                    │              ▼          │
                    │   Discover     Validate      Load    Register Hooks    Collect Tasks
                    │              │          │
                    │              │          │
                    └──────────────┘───────────────────────┘
                                   │
                    ┌───────────────────────────────────────────────┐
                    │     Core Polycode Application      │
                    │         (uses modules via __init__.py)   │
                    └───────────────────────────────────────────────┘
```

---

## 📦 Module Breakdown

### 1. Entry Point (`__init__.py`)

**Purpose:** Central export hub for all module subsystems.

**Exports:**

- `ChannelRegistry` — Notification channel management
- `ModuleContext` — Shared context/dataclass
- `FlowEvent` — Flow lifecycle event enum
- `FlowHookSpec` — Hook specification class
- `get_plugin_manager` — Plugin manager accessor
- `hookimpl` — Hook implementation marker
- `hookspec` — Hook specification marker
- `PolycodeModule` — Module protocol
- `ModuleRegistry` — Module registry class
- `TaskRegistry` — Celery task registry
- `get_task_registry` — Task registry accessor
- `reset_task_registry` — Task registry reset (testing)

---

### 2. Channel Registry (`channels.py`)

**Purpose:** Provides a unified system for sending notifications during flow execution.

**Key Classes:**

```python
from modules.channels import ChannelRegistry

# Register a channel factory
ChannelRegistry.register(
    ChannelType.SLACK,
    lambda config, project: SlackChannel(
        token=config.extra.get("token"),
        channel_id=config.extra.get("channel_id"),
    )
)

# Create a channel instance
channel = ChannelRegistry.create_channel(
    channel_type=ChannelType.SLACK,
    config=ChannelConfig(
        type="slack",
        extra={"token": "xoxb-...", "channel_id": "C123"},
    ),
    project_config=project_config,
)
```

**Benefits:**

- 🔌 Modules don't need to know channel implementation details
- 🎯 Easy to test by swapping channel implementations
- 📡 Supports multiple notification types: Slack, GitHub, Redis, email, etc.

---

### 3. Module Context (`context.py`)

**Purpose:** Provides shared context passed to all modules during initialization.

**Available Data:**

```python
@dataclass
class ModuleContext:
    db_engine: Engine                 # SQLAlchemy database engine
    db_url: str                       # Database connection URL
    hook_manager: PluginManager        # Hook manager instance
    config: dict[str, Any]           # Module-specific config

    # Get config for specific module
    context.get_module_config("my_module")  # Returns dict[str, Any]
```

**Usage in Modules:**

```python
class MyModule(PolycodeModule):
    def on_load(cls, context: ModuleContext):
        db_engine = context.db_engine
        hook_manager = context.hook_manager

        # Register module-specific hooks
        hook_manager.register_hooks(cls, context)
```

---

### 4. Hooks System (`hooks.py`)

**Purpose:** Event-based hook system for flow orchestration.

**Key Components:**

- **`FlowEvent` enum** — Lifecycle events:

  ```python
  class FlowEvent(StrEnum):
      SETUP = "SETUP"
      FLOW_STARTED = "flow_started"
      FLOW_FINISHED = "flow_finished"
      FLOW_ERROR = "flow_error"
      CREW_FINISHED = "crew_finished"
      STORY_COMPLETED = "story_completed"
      CLEANUP = "cleanup"
  ```

- **`FlowHookSpec` class** — Hook specification for filtering events by type and label
- **`@hookimpl` decorator** — Mark methods as hook implementations
- **`@hookspec` decorator** — Define hook specifications

**Example Hook Implementation:**

```python
from modules.hooks import FlowEvent, hookimpl, FlowHookSpec

class MyHooks:
    @hookimpl
    def on_flow_event(self, event, flow_id, state, result=None, label=""):
        if event == FlowEvent.CREW_FINISHED and label == "plan":
            print(f"Planning crew finished in flow {flow_id}")

        if event == FlowEvent.STORY_COMPLETED:
            self.git_ops.commit_and_push(state, result)

        if event == FlowEvent.FLOW_FINISHED:
            self.finalize_flow(flow_id, state)
```

**Event Flow:**

1. Flow starts → `FLOW_STARTED` event fires
2. Task completes → `CREW_FINISHED` or `STORY_COMPLETED` events fire
3. Hooks filter by event type and label
4. Hook implementations respond to specific events

---

### 5. Module Protocol (`protocol.py`)

**Purpose:** Defines the interface that all modules must implement.

**Protocol Requirements:**

```python
@runtime_checkable
class PolycodeModule(Protocol):
    """Protocol that all modules (built-in and external) must satisfy."""

    name: ClassVar[str]                    # Unique module identifier
    version: ClassVar[str] = "0.0.0"       # Semantic version
    dependencies: ClassVar[list[str]] = []      # Module names that must load first

    @classmethod
    def on_load(cls, context: ModuleContext) -> None:
        """
        Called after all models are registered and tables created.

        Initialize module resources (DB connections, caches, etc.).
        """
        ...

    @classmethod
    def register_hooks(cls, hook_manager: PluginManager) -> None:
        """
        Register hook implementations.

        Modules that don't use hooks can no-op.
        """
        ...

    @classmethod
    def get_models(cls) -> list[type]:
        """
        Return ORM model classes for this module.

        Optional — models are auto-registered via RegisteredBase.
        """
        return []

    @classmethod
    def get_celery_tasks(cls) -> list[dict[str, Any]]:
        """
        Return Celery task definitions for this module.

        Each dict should contain:
        - name: str - Task name (prefixed with module name)
        - func: Callable - Task function
        - options: dict (optional) - Task options
        """
        return []
```

**Module Loading Flow:**

1. External module defines an entry point: `entry_points["polycode.modules"]`
2. `ModuleRegistry.discover()` finds it and loads the class
3. Validates `dependencies` (other modules load first)
4. Calls `on_load(context)` with `ModuleContext`
5. Calls `register_hooks(hook_manager)` to collect hook implementations
6. Collects `get_celery_tasks()` and registers with Celery app
7. Raises error on circular dependencies

---

### 6. Module Registry (`registry.py`)

**Purpose:** Discovers external modules and manages their lifecycle.

**Key Methods:**

```python
from modules.registry import ModuleRegistry

# Discover all external modules
registry = ModuleRegistry()
registry.discover(context=context)

# Register a built-in module
registry.register_builtin(MyModule)

# Load all modules in dependency order
registry.load_all(context=context)

# Get loaded modules
modules = registry.modules  # dict[str, PolycodeModule]
```

**Discovery Mechanism:**

1. Scans `entry_points()` for `group="polycode.modules"`
2. Validates class has `name` and `dependencies` attributes
3. Uses **Kahn's algorithm** for topological sorting
4. Raises `RuntimeError` if circular dependency detected

**Example Module Definition:**

```python
from modules.protocol import PolycodeModule

@runtime_checkable
class MyModule(PolycodeModule):
    """My custom Polycode module."""

    name: ClassVar[str] = "my_module"
    version: ClassVar[str] = "1.0.0"
    dependencies: ClassVar[list[str]] = []

    @classmethod
    def on_load(cls, context: ModuleContext) -> None:
        # Initialize module
        context.config["my_module"] = {"enabled": True}
        print(f"📦 Module {cls.name} loaded")
```

**Entry Point Registration (in main app):**

```python
from importlib.metadata

# Register custom module
entry_points.register(
    group="polycode.modules",
    name="my_module",
    load=MyModule,
)
)
```

---

### 7. Task Registry (`tasks.py`)

**Purpose:** Registers Celery tasks contributed by modules with the Celery application.

**Key Features:**

- **Global task registry** — Singleton pattern for task registration
- **Module namespace** — Tasks are prefixed with module name (e.g., `my_module.process_data`)
- **Validation** — Ensures tasks have `name`, `func` fields
- **Celery integration** — Auto-registers with `@celery.task` decorator

**Registering a Module Task:**

```python
from tasks import TaskRegistry

# In your module's get_celery_tasks():
def get_celery_tasks(cls):
    return [
        {"name": "process_data", "func": process_data_task, "options": {"bind": True}},
        {"name": "cleanup", "func": cleanup_task},
    ]

# Register tasks (happens in load_all())
from modules.tasks import get_task_registry

# Tasks get auto-registered during module loading
```

**Task Options:**

- `bind=True` — Bind task arguments to Celery
- `max_retries` — Retry on failure
- `countdown` — Countdown/eta tasks
- `time_limit` — Task timeout

---

## 🚀 Creating a Custom Module

### Step 1: Define Your Module

Create a Python module that implements `PolycodeModule`:

```python
# my_plugin/my_module.py

from modules.protocol import PolycodeModule
from modules.hooks import FlowEvent, hookimpl, FlowHookSpec

@runtime_checkable
class MyPlugin(PolycodeModule):
    """Custom Polycode module example."""

    name = ClassVar[str] = "my_plugin"
    version = ClassVar[str] = "1.0.0"
    dependencies = []  # No dependencies

    @classmethod
    def on_load(cls, context: ModuleContext) -> None:
        """Initialize plugin resources."""
        # Access shared database engine
        db_engine = context.db_engine

        # Register notification channel
        from modules.channels import ChannelRegistry
        ChannelRegistry.create_channel(...)

        print(f"✅ {cls.name} loaded")

    @classmethod
    def register_hooks(cls, hook_manager: PluginManager) -> None:
        """Register flow event handlers."""
        @hookimpl
        def on_flow_event(self, event, flow_id, state, result=None, label=""):
            if event == FlowEvent.CREW_FINISHED and label == "plan":
                print(f"🏹 Crew finished planning in flow {flow_id}")

        @hookspec
        def spec(self):
            return FlowHookSpec(
                event=FlowEvent.CREW_FINISHED,
                label="plan",
                method="on_flow_event"
            )

        hook_manager.register_hooks(cls, context)
```

### Step 2: Register Entry Point

Register your module with the entry point system:

```python
# main.py

from importlib.metadata

# In your app's entry point or plugin loader:
def register_modules():
    entry_points.register(
        group="polycode.modules",
        name="my_plugin",
        load=MyPlugin,  # Your module class
    )
```

### Step 3: Configure Channel

If you want notifications (Slack, GitHub, etc.), configure in your app config or environment:

```python
# config/modules.yaml or .env
MY_PLUGIN_CHANNEL=slack
MY_PLUGIN_SLACK_TOKEN=xoxb-...

# In your module:
from modules.channels import ChannelRegistry, ChannelType

channel = ChannelRegistry.create_channel(
    channel_type=ChannelType.SLACK,
    config=ChannelConfig(
        type="slack",
        extra={"token": os.getenv("MY_PLUGIN_SLACK_TOKEN")},
    ),
)
```

---

## 🔌 Flow Integration

The hook system integrates with Polycode's CrewAI flows:

### Flow Lifecycle Events

| Event             | When It Fires             | Typical Hook Response                      |
| ----------------- | ------------------------- | ------------------------------------------ |
| `SETUP`           | Flow starts               | Prepare resources, validate state          |
| `FLOW_STARTED`    | Crew begins execution     | Lock resources, notify stakeholders        |
| `CREW_FINISHED`   | Crew planning complete    | Review output, create implementation tasks |
| `STORY_COMPLETED` | Story implementation done | Run cleanup tasks                          |
| `FLOW_FINISHED`   | Flow execution complete   | Finalize, run cleanup, mark story complete |
| `FLOW_ERROR`      | Flow failed               | Handle errors, notify team                 |

### Implementing Flow Hooks

```python
from modules.hooks import FlowEvent, hookimpl, FlowHookSpec, get_plugin_manager

class FlowHooks:
    @hookimpl
    def __init__(self, git_ops):
        self.git_ops = git_ops

    @hookspec
    def on_crew_finished(self):
        return FlowHookSpec(
            event=FlowEvent.CREW_FINISHED,
            label="plan",
            method="on_crew_finished"
        )

    def on_crew_finished(self, flow_id, state, result=None, label=""):
        """Handle crew completion event."""
        print(f"🏹 Crew finished: {result}")

    @hookspec
    def on_flow_finished(self):
        return FlowHookSpec(
            event=FlowEvent.FLOW_FINISHED,
            label="",
            method="on_flow_finished"
        )

    def on_flow_finished(self, flow_id, state, result=None, label=""):
        """Handle flow completion event."""
        # Create PR or finalize changes
        self.git_ops.commit_and_push(state, result)

    @hookspec
    def on_cleanup(self):
        return FlowHookSpec(
            event=FlowEvent.CLEANUP,
            label="",
            method="on_cleanup"
        )

    def on_cleanup(self, flow_id, state, result=None, label=""):
        """Handle cleanup event."""
        print(f"🧹 Cleaning up resources for flow {flow_id}")
```

**Registering Hooks:**

```python
from modules.hooks import get_plugin_manager

class MyFlowHooks:
    pass  # Hooks get auto-registered during plugin load

# Manually register if needed
hook_manager = get_plugin_manager()
hook_manager.register_hooks(MyFlowHooks, context)
```

---

## 🧪 Testing

### Testing Modules in Isolation

Each module can be tested independently by mocking dependencies:

```python
# tests/test_my_module.py

import pytest
from unittest.mock import MagicMock
from modules.context import ModuleContext
from my_plugin import MyPlugin

def test_on_load():
    # Arrange
    context = ModuleContext(
        db_engine=MagicMock(),
        db_url="postgresql://test",
        hook_manager=MagicMock(),
    )

    # Act
    MyPlugin.on_load(context)

    # Assert
    # Verify module initialized correctly
```

### Resetting Module Registry

```python
from modules.registry import ModuleRegistry

# Clear and reset registry
ModuleRegistry.reset()

# Discover and load fresh
registry = ModuleRegistry()
registry.discover(context=context)
```

### Testing Hook Implementations

```python
# tests/test_hooks.py

from modules.hooks import FlowEvent, hookimpl, FlowHookSpec, get_plugin_manager

@pytest.fixture
def plugin_manager():
    pm = get_plugin_manager()
    pm.add_hookspecs(MyHookSpecs())
    return pm

def test_hook_filters_by_event():
    """Test that hooks only fire for matching events."""
    pass  # Implementation example
```

---

## 📝 Best Practices

### Module Development

✅ **Always implement `PolycodeModule` protocol** — This ensures proper integration
✅ **Use `dependencies` for module ordering** — Registry handles load order
✅ **Keep `on_load()` lightweight** — Only initialize resources, don't run heavy operations
✅ **Use `get_celery_tasks()` for background work** — Don't block module load
✅ **Register hooks if needed** — Even if your module doesn't use events, implement no-op methods
✅ **Add docstrings** — Explain your module's purpose in `on_load()` or class docstring

### Hook Development

✅ **Use `@hookimpl` decorator** — Marks methods as hook implementations
✅ **Use `@hookspec` decorator** — Defines which events trigger which methods
✅ **Handle optional parameters** — `result=None, label=""` provide context
✅ **Keep hooks focused** — Single responsibility for each hook method

### Naming Conventions

| Type      | Convention                   | Example                                        |
| --------- | ---------------------------- | ---------------------------------------------- |
| Modules   | `lowercase_with_underscores` | `my_module.py`                                 |
| Classes   | `PascalCase`                 | `ChannelRegistry`                              |
| Functions | `snake_case`                 | `create_channel`, `on_load`                    |
| Tasks     | `snake_case`                 | `process_data_task`, prefixed with module name |

### Error Handling

```python
# Always handle missing dependencies gracefully
if not module_name in self._modules:
    log.warning(f"⚠️ Module '{name}' depends on '{dep}' which is not registered")
    # Continue loading with available modules
```

---

## 🔧 Troubleshooting

### Module Not Loading

**Issue:** Your module entry point is registered but not loading.

**Check:**

```python
# Verify entry point is registered
from modules.registry import ModuleRegistry
registry = ModuleRegistry()
print(registry.registered_types())

# Check if module is discovered
print(registry.discover(context=context))
```

**Common Causes:**

- Entry point not registered with `entry_points.register()`
- Class doesn't have `name` attribute
- Class fails to import (syntax error)

---

### Circular Dependencies Detected

**Issue:** Registry raises `RuntimeError: Circular dependency detected among modules`

**Solution:**

1. Check all module `dependencies` lists
2. Ensure dependencies are actually registered
3. Use `registry.discover()` to validate before loading

---

### Hooks Not Firing

**Issue:** Your hook method isn't being called during flow execution.

**Check:**

```python
# Verify hook is registered
from modules.hooks import get_plugin_manager

pm = get_plugin_manager()
print(pm.get_hookspecs())
```

**Common Causes:**

- `@hookspec` decorator not used
- Event/label combination doesn't match flow event
- Hook implementation not registered with plugin manager

---

### Tasks Not Registering

**Issue:** Your module's tasks aren't showing up in Celery.

**Check:**

```python
# Verify task registration
from tasks import get_task_registry
registry = get_task_registry()
print(registry.tasks)
```

**Common Causes:**

- `get_celery_tasks()` returns empty list
- Module `name` attribute doesn't match registry
- Task definition missing `name` or `func` field

---

## 🚀 Advanced Topics

### Async Task Execution

Tasks registered via `TaskRegistry` can use Celery features:

```python
# In your module's task definition
def process_data_task(data: dict):
    # Process data
    pass

# Task definition in get_celery_tasks()
{
    "name": "process_data",
    "func": process_data_task,
    "options": {
        "bind": True,          # Bind task arguments
        "max_retries": 3,    # Retry on failure
        "countdown": 1,       # Countdown task
    }
}
```

### Multiple Channel Types

Support multiple notification channels simultaneously:

```python
from modules.channels import ChannelRegistry, ChannelType

# Configure channels in context
context.config["channels"] = {
    "slack": {"enabled": True, "token": "...", "channel_id": "..."},
    "github": {"enabled": True, "token": "..."},
    "email": {"enabled": False},
}

# In your module, send notifications:
ChannelRegistry.create_channel(
    channel_type=ChannelType.SLACK,
    config=ChannelConfig(...),
)
 context=context,
)
```

### Conditional Hook Logic

Create conditional hooks based on flow labels or configuration:

```python
from modules.hooks import FlowEvent, hookimpl, FlowHookSpec

class ConditionalHooks:
    @hookimpl
    @hookspec
    def on_flow_finished_with_label(self):
        return FlowHookSpec(
            event=FlowEvent.FLOW_FINISHED,
            label="custom_label",  # Only fires for this label
            method="on_flow_finished_with_label"
        )

    def on_flow_finished_with_label(self, flow_id, state, result=None, label=""):
        if label == "custom_label":
            print(f"🏹 Flow {flow_id} finished with custom label")
        else:
            print(f"🏹 Flow {flow_id} finished (no custom label)")
```

### Shared State Between Hooks

Use instance variables or class-level state to share data across hooks:

```python
class FlowHooks:
    def __init__(self):
        self.state = {}  # Shared state storage

    @hookimpl
    @hookspec
    def on_flow_finished(self, ...):
        # Store result in state
        self.state["last_result"] = result

    @hookimpl
    @hookspec
    def on_cleanup(self, ...):
        # Access stored result
        print(f"🧹 Last result: {self.state.get('last_result')}")
```

---

## 📚 License

Part of the Polycode project. See main project LICENSE file.

## 🤝 Contributing

When contributing modules to Polycode:

1. Follow the `PolycodeModule` protocol
2. Add comprehensive docstrings
3. Implement hooks if needed
4. Return tasks from `get_celery_tasks()` if using Celery
5. Use `ModuleContext` for shared resources
6. Test thoroughly

## 📚 Support

For questions or issues:

- Open an issue in the main Polycode repository
- Tag with `modules` and include the module name
- Include error logs and reproduction steps

---

## 📚 Version History

| Version | Changes                              |
| ------- | ------------------------------------ |
| 0.0.0   | Initial plugin system implementation |
