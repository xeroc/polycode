# Polycode Flow System

> **Status**: Implemented
> **Last Updated**: 2026-03-24

## Overview

The Flow System provides a plugin-based architecture for running different CrewAI flows based on GitHub issue labels. This enables extensible, label-driven workflow orchestration where new flows can be added without modifying core code.

## Architecture

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              FLOW EXECUTION PATH                             │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  GitHub Webhook                                                              │
│       │                                                                      │
│       ▼                                                                      │
│  ┌─────────────────────────────────┐                                        │
│  │ github_app webhook          │                                        │
│  │   - Extract label from payload  │                                        │
│  │   - Match against FlowRegistry  │                                        │
│  │   - Trigger Celery task        │                                        │
│  └──────────────┬──────────────────┘                                        │
│                 │                                                            │
│                 ▼                                                            │
│  ┌─────────────────────────────────┐      ┌─────────────────────────────┐   │
│  │ kickoff_feature_dev_task()   │─────▶│ FlowRegistry                │   │
│  │   - Build KickoffIssue          │      │   - get_flow(name)          │   │
│  │   - Lookup flow in registry     │      │   - get_flow_for_label()    │   │
│  │   - Execute flow.kickoff()      │      │   - list_flows()            │   │
│  └─────────────────────────────────┘      └──────────────┬──────────────┘   │
│                                                          │                   │
│                                                          ▼                   │
│                                           ┌─────────────────────────────┐    │
│                                           │ FlowDef                     │    │
│                                           │   - name: str               │    │
│                                           │   - kickoff_func: Callable  │    │
│                                           │   - supported_labels: list  │    │
│                                           │   - description: str        │    │
│                                           └─────────────────────────────┘    │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────┐
│                              PLUGIN DISCOVERY                                │
├──────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌─────────────────────────────────┐                                        │
│  │ bootstrap()                     │                                        │
│  │   1. Load external modules      │  (entry_points["polycode.modules"])    │
│  │   2. Register built-in modules  │                                        │
│  │   3. Create DB tables           │                                        │
│  │   4. Load all modules           │                                        │
│  │      - on_load()                │                                        │
│  │      - register_hooks()         │                                        │
│  │      - collect_flows()          │                                        │
│  │      - collect_celery_tasks()   │                                        │
│  └─────────────────────────────────┘                                        │
│                                                                              │
│  Module Protocol (PolycodeModule):                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │ class MyModule:                                                         ││
│  │     name = "my-module"                                                  ││
│  │     version = "1.0.0"                                                   ││
│  │     dependencies = []                                                   ││
│  │                                                                         ││
│  │     @classmethod                                                        ││
│  │     def on_load(cls, context): ...                                      ││
│  │                                                                         ││
│  │     @classmethod                                                        ││
│  │     def register_hooks(cls, pm): ...                                    ││
│  │                                                                         ││
│  │     @classmethod                                                        ││
│  │     def get_flows(cls) -> list[FlowDef]: ...                            ││
│  │                                                                         ││
│  │     @classmethod                                                        ││
│  │     def get_celery_tasks(cls) -> list[dict]: ...                        ││
│  └─────────────────────────────────────────────────────────────────────────┘│
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## Core Components

### 1. FlowDef

A dataclass defining a flow's metadata and entry point.

```python
from dataclasses import dataclass
from typing import Callable

@dataclass
class FlowDef:
    """Definition of a flow that can be triggered by labels."""

    name: str
    """Unique flow identifier (e.g., "ralph", "code-review")."""

    kickoff_func: Callable[[KickoffIssue], None]
    """Entry point function that runs flow. Receives KickoffIssue."""

    description: str = ""
    """Human-readable description of what this flow does."""

    supported_labels: list[str] = []
    """Labels that trigger this flow (without prefix).
    E.g., ["implement", "review"] matches "polycode:implement", "polycode:review".
    Empty list means flow can only be triggered via explicit flow_name parameter.
    """

    priority: int = 0
    """When multiple flows match a label, higher priority wins."""
```

### 2. FlowRegistry

Central registry for all available flows.

```python
class FlowRegistry:
    """Registry for flow definitions contributed by modules."""

    def register(self, flow_def: FlowDef) -> None:
        """Register a flow definition.

    Args:
            flow_def: Flow definition to register.

        Raises:
            ValueError: If flow name is empty or kickoff_func is not callable.
        """

    def get_flow(self, name: str) -> FlowDef | None:
        """Get a flow by name.

    Args:
            name: Flow identifier.

        Returns:
            FlowDef if found, None otherwise.
        """

    def get_flow_for_label(self, label: str) -> FlowDef | None:
        """Find a flow that handles given label.

        Matches label against each flow's supported_labels (with prefix stripping).
        Returns highest priority match.

    Args:
            label: Full label string (e.g., "polycode:implement").

        Returns:
            FlowDef if match found, None otherwise.
        """

    def list_flows(self) -> list[str]:
        """List all registered flow names."""

    def collect_from_modules(self, modules: dict[str, Any]) -> int:
        """Collect flows from all modules.

        Called by bootstrap() after modules are loaded.

        Args:
            modules: Dict of module_name -> module class.

        Returns:
            Number of flows collected.
        """
```

### 3. Global Label Prefix

All flow-triggering labels share a configurable prefix:

```python
# src/flows/protocol.py
FLOW_LABEL_PREFIX: str = "polycode:"
"""Prefix for all flow-triggering labels. Labels must match: {prefix}{label}"""
```

The registry strips this prefix when matching against `supported_labels`:

```
Label: "polycode:implement"
Prefix: "polycode:"
Stripped: "implement"
Matches: FlowDef.supported_labels = ["implement"]
```

---

## File Structure

```
src/
├── flows/
│   ├── __init__.py           # Export FlowDef, FlowRegistry, get_flow_registry
│   ├── base.py             # Base flow classes (FlowIssueManagement, KickoffIssue)
│   ├── protocol.py          # FlowDef dataclass
│   ├── registry.py          # FlowRegistry class
│   └── ralph/              # Ralph flow module
│       ├── __init__.py       # Export kickoff, RalphLoopFlow
│       ├── flow.py           # RalphLoopFlow class definition
│       ├── module.py         # RalphModule (PolycodeModule implementation)
│       └── types.py          # RalphLoopState, RalphOutput
│
├── modules/
│   ├── protocol.py          # PolycodeModule protocol (add get_flows method)
│   ├── registry.py          # ModuleRegistry (add flow collection)
│   ├── hooks.py            # FlowEvent hooks
│   ├── context.py          # ModuleContext
│   └── tasks.py            # Celery task collection
│
├── celery_tasks/
│   └── flow_orchestration.py # kickoff_feature_dev_task (with flow_name param)
│
├── github_app/
│   ├── app.py              # FastAPI application
│   └── webhook_handler.py  # Webhook processing (uses FlowRegistry)
│
├── cli/
│   └── flow.py            # Flow CLI commands (list, run, status)
│
└── bootstrap.py              # Register RalphModule, collect flows
```

---

## Usage

### CLI Flow Commands

```bash
# List available flows
polycode flow list

# Run Ralph flow (feature development)
polycode flow run ralph --issue 42

# Show flow status
polycode flow status --flow-id <id>
```

### Creating a New Flow

1. **Create flow module** in `src/flows/<name>/`:

```python
# src/flows/my_flow/flow.py
from flows.base import FlowIssueManagement, KickoffIssue
from pydantic import BaseModel

class MyFlowState(BaseModel):
    # ... state fields ...

class MyFlow(FlowIssueManagement[MyFlowState]):
    @start()
    def begin(self):
        # ... flow logic ...

def kickoff(issue: KickoffIssue) -> None:
    """Entry point for MyFlow."""
    flow = MyFlow()
    flow.kickoff(inputs={...})
```

1. **Create module class**:

```python
# src/flows/my_flow/module.py
from flows.protocol import FlowDef
from modules.protocol import PolycodeModule

class MyFlowModule:
    """Module providing MyFlow."""

    name = "my-flow"
    version = "1.0.0"
    dependencies: list[str] = []

    @classmethod
    def on_load(cls, context: "ModuleContext"):
        pass

    @classmethod
    def register_hooks(cls, hook_manager: "pluggy.PluginManager"):
        pass

    @classmethod
    def get_flows(cls) -> list[FlowDef]:
        from .flow import kickoff
        return [
            FlowDef(
                name="my-flow",
                kickoff_func=kickoff,
                description="Does something useful",
                supported_labels=["my-action"],  # Matches "polycode:my-action"
            )
        ]
```

1. **Register in bootstrap.py**:

```python
from flows.my_flow.module import MyFlowModule
module_registry.register_builtin(MyFlowModule)
```

1. **Add label in GitHub**:
   - Create label: `polycode:my-action`
   - Add to issue → triggers MyFlow

### Triggering Flows Programmatically

```python
from flows.registry import get_flow_registry
from flows.base import KickoffIssue

# Get flow by name
flow_def = get_flow_registry().get_flow("ralph")
flow_def.kickoff_func(issue)

# Get flow for label
flow_def = get_flow_registry().get_flow_for_label("polycode:implement")
if flow_def:
    flow_def.kickoff_func(issue)
```

---

## Label Matching Rules

1. **Prefix stripping**: Labels must start with `FLOW_LABEL_PREFIX` (default: "polycode:")
2. **Exact match**: Stripped label must exactly match an entry in `supported_labels`
3. **Priority resolution**: If multiple flows match, highest `priority` wins
4. **Fallback**: If no match found, system falls back to "ralph" flow

### Examples

| Label                | Prefix      | Stripped    | Matches FlowDef.supported_labels |
| -------------------- | ----------- | ----------- | -------------------------------- |
| `polycode:implement` | `polycode:` | `implement` | `["implement"]` ✓                |
| `polycode:review`    | `polycode:` | `review`    | `["review"]` ✓                   |
| `bug`                | `polycode:` | N/A         | No match (missing prefix)        |
| `polycode:implement` | `polycode:` | `implement` | `["foo", "bar"]` ✗               |

---

## Configuration

### Environment Variables

```bash
# Label prefix (default: "polycode:")
FLOW_LABEL_PREFIX=polycode:

# Default flow when no label match (default: "ralph")
DEFAULT_FLOW=ralph
```

---

## Module Protocol Extension

The `PolycodeModule` protocol includes:

```python
@runtime_checkable
class PolycodeModule(Protocol):
    name: ClassVar[str]
    version: ClassVar[str] = "0.0.0"
    dependencies: ClassVar[list[str]] = []

    @classmethod
    def on_load(cls, context: "ModuleContext") -> None:
        """Called after all models are registered and tables created."""
        ...

    @classmethod
    def register_hooks(cls, hook_manager: "pluggy.PluginManager") -> None:
        """Register hook implementations."""
        ...

    @classmethod
    def get_flows(cls) -> list["FlowDef"]:
        """Return flow definitions provided by this module.

        Each flow can declare which labels it handles via supported_labels.
        Labels are matched against FLOW_LABEL_PREFIX (default: "polycode:").

        Returns:
            List of FlowDef instances. Empty list if module provides no flows.
        """
        return []

    @classmethod
    def get_celery_tasks(cls) -> list[dict[str, Any]]:
        """Return Celery task definitions provided by this module."""
        return []
```

---

## Ralph Flow (Feature Development)

Ralph flow implements feature development with per-story commits:

```python
from flows.base import FlowIssueManagement
from pydantic import BaseModel

class RalphLoopState(BaseModel):
    issue_id: int
    issue_title: str
    task: str
    repo: str
    branch: str
    stories: list = []
    completed_stories: list = []

class RalphLoopFlow(FlowIssueManagement[RalphLoopState]):
    @start()
    def setup(self):
        """Initialize worktree and discover AGENTS.md."""
        self._emit(FlowEvent.FLOW_STARTED, label="ralph")
        self._prepare_work_tree()
        self._discover_agents_md()

    @listen(setup)
    def plan(self):
        """Generate plan with stories."""
        result = PlanCrew().crew().kickoff(...)
        self.state.stories = result.pydantic.stories

    @listen(plan)
    def implement(self):
        """Implement each story."""
        for story in unfinished_stories:
            result = ImplementCrew().crew().kickoff(...)
            self._test()
            self._commit_and_push()
            self._emit(FlowEvent.STORY_COMPLETED, result=story, label=str(story.id))

    @listen(implement)
    def verify_build(self):
        """Final verification."""
        self._build()
        self._test()
        self._emit(FlowEvent.FLOW_FINISHED, label="ralph")
```

**Key Points:**

- Worktree for isolated execution
- AGENTS.md discovery for build/test commands
- Per-story commits and pushes
- Hook system for PR creation and merging

---

## Error Handling

| Scenario                     | Behavior                                       |
| ---------------------------- | ---------------------------------------------- |
| Unknown flow name            | Log warning, fall back to "ralph"              |
| No flow matches label        | Fall back to "ralph"                           |
| Flow raises exception        | Task retries (Celery), eventually fails        |
| Empty supported_labels       | Flow only triggerable via explicit `flow_name` |
| Circular module dependencies | RuntimeError during bootstrap                  |

---

## Future Enhancements

1. **Flow chaining**: One flow can trigger another
2. **Conditional labels**: Flow declares `label_patterns` with regex/glob support
3. **Flow versioning**: Multiple versions of same flow, selection by config
4. **Flow status tracking**: DB table tracking flow execution per issue
5. **Flow cancellation**: Stop running flow when label removed

---

## References

- [PLUGIN.md](./PLUGIN.md) - Plugin architecture details
- [HOOK_ARCHITECTURE.md](./HOOK_ARCHITECTURE.md) - Flow event hooks
- [src/AGENTS.md](../src/AGENTS.md) - CrewAI patterns
