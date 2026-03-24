# Polycode Architecture

## Design Philosophy

Polycode is a multi-agent software development automation system that integrates with GitHub Projects and uses CrewAI for orchestrating AI coding workflows. It provides:

1. **Label-driven workflow orchestration** - GitHub issue labels trigger different flows
2. **Plugin architecture** - Extensible module system for hooks and models
3. **CrewAI-based crews** - Teams of AI agents for planning, implementing, reviewing code
4. **Celery integration** - Background processing for long-running workflows
5. **GitHub integration** - Webhook-driven event handling and project management

## Core Concepts

### Polycode → CrewAI Mapping

| Polycode              | CrewAI                 |
| --------------------- | ---------------------- |
| Flow                  | Crew or Flow           |
| Subcommand (flow cmd) | Task / Agent           |
| Issue/Story           | Context/State          |
| Module hooks          | Plugin system          |
| Label-triggering      | Dynamic flow selection |

### Directory Structure

```
apps/polycode/
├── src/
│   ├── cli/                    # Typer-based CLI interface
│   │   ├── main.py             # Main entry point
│   │   ├── project.py          # Project management commands
│   │   ├── flow.py            # Flow execution commands
│   │   ├── server.py           # Webhook server commands
│   │   ├── worker.py           # Celery worker commands
│   │   └── db.py              # Database commands
│   ├── flows/                   # Flow definitions and registry
│   │   ├── base.py             # Base flow classes
│   │   ├── protocol.py          # FlowDef dataclass
│   │   ├── registry.py          # FlowRegistry
│   │   └── ralph/              # Ralph flow (feature development)
│   │       ├── flow.py         # RalphLoopFlow
│   │       ├── module.py       # RalphModule
│   │       └── types.py        # Ralph state types
│   ├── crews/                   # CrewAI crew implementations
│   │   ├── ralph_crew/        # Development crew
│   │   ├── plan_crew/         # Planning crew
│   │   ├── implement_crew/     # Implementation crew
│   │   ├── review_crew/        # Review crew
│   │   └── verify_crew/        # Verification crew
│   ├── modules/                 # Plugin system
│   │   ├── protocol.py          # PolycodeModule protocol
│   │   ├── hooks.py            # FlowEvent hooks
│   │   ├── context.py          # ModuleContext
│   │   ├── registry.py          # ModuleRegistry
│   │   └── tasks.py            # Celery task collection
│   ├── project_manager/         # GitHub integration
│   │   ├── github.py           # GitHub API client
│   │   ├── types.py            # ProjectConfig, StatusMapping
│   │   └── config.py           # Settings
│   ├── persistence/             # Database layer
│   │   ├── postgres.py          # Core models
│   │   └── registry.py          # ModelRegistry
│   ├── github_app/              # FastAPI webhook server
│   │   ├── app.py              # FastAPI application
│   │   └── webhook_handler.py  # Webhook processing
│   ├── celery_tasks/            # Celery task definitions
│   │   ├── flow_orchestration.py
│   │   ├── agent_execution.py
│   │   ├── webhook_tasks.py
│   │   └── utility_tasks.py
│   ├── gitcore/                # Git operations
│   │   ├── gitops.py          # Git operations
│   │   └── hooks.py            # Git hooks
│   ├── retro/                  # Retrospectives module
│   │   ├── persistence.py
│   │   └── hooks.py
│   ├── models/                  # Additional database models
│   └── bootstrap.py             # Plugin initialization
├── tests/                      # Test suite
├── pyproject.toml              # Dependencies and scripts
├── README.md                   # Main documentation
└── .env                       # Environment variables
```

## Component Breakdown

### CLI (src/cli/)

Typer-based CLI with subcommands:

```python
app = typer.Typer(name="polycode", help="Multi-agent software development automation")
app.add_typer(server_app, name="server")
app.add_typer(worker_app, name="worker")
app.add_typer(flow_app, name="flow")
app.add_typer(project_app, name="project")
app.add_typer(db_app, name="db")
```

**Key Points:**

- Main entry: `polycode` command
- Subcommands: `server`, `worker`, `flow`, `project`, `db`
- Environment-based logging with `--log-level` and `-v` flags

### Flows (src/flows/)

Flow system with label-based triggering:

```python
@dataclass
class FlowDef:
    name: str
    kickoff_func: Callable[[KickoffIssue], None]
    description: str = ""
    supported_labels: list[str] = []
    priority: int = 0

class FlowRegistry:
    def register(self, flow_def: FlowDef) -> None
    def get_flow(self, name: str) -> FlowDef | None
    def get_flow_for_label(self, label: str) -> FlowDef | None
    def list_flows(self) -> list[str]
```

**Key Points:**

- Flows define which labels they handle (e.g., `["implement"]` matches `"polycode:implement"`)
- `FlowRegistry` manages all registered flows
- Label prefix (`polycode:`) is stripped before matching
- Fallback to `"ralph"` flow if no label match

### Crews (src/crews/)

CrewAI crew implementations:

```python
from crewai import Flow, listen, start
from crews.base import PolycodeCrew

@CrewBase
class PlanCrew(PolycodeCrew):
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"
    crew_label = "plan"

    @agent
    def planner(self) -> Agent:
        return Agent(config=self.agents_config["planner"])  # type: ignore[index]
```

**Key Points:**

- `PolycodeCrew` base class auto-emits `CREW_FINISHED` events
- `crew_label` used for hook filtering
- YAML config for agents and tasks
- Type-safe with `# type: ignore[index]` comments

### Modules (src/modules/)

Plugin system for extensions:

```python
@runtime_checkable
class PolycodeModule(Protocol):
    name: ClassVar[str]
    version: ClassVar[str] = "0.0.0"
    dependencies: ClassVar[list[str]] = []

    @classmethod
    def on_load(cls, context: "ModuleContext") -> None

    @classmethod
    def register_hooks(cls, hook_manager: "pluggy.PluginManager") -> None

    @classmethod
    def get_flows(cls) -> list["FlowDef"]

    @classmethod
    def get_celery_tasks(cls) -> list[dict[str, Any]]
```

**Key Points:**

- Module protocol with `on_load`, `register_hooks`, `get_flows`, `get_celery_tasks`
- Entry point discovery via `polycode.modules` group
- Built-in modules registered explicitly in `bootstrap.py`
- Topological sort for dependency loading

### Flow Events (src/modules/hooks.py)

Simplified 5-event hook system:

```python
class FlowEvent(StrEnum):
    FLOW_STARTED = "flow_started"
    FLOW_FINISHED = "flow_finished"
    FLOW_ERROR = "flow_error"
    CREW_FINISHED = "crew_finished"
    STORY_COMPLETED = "story_completed"

@hookimpl
def on_flow_event(
    event: FlowEvent,
    flow_id: str,
    state: object,
    result: object | None = None,
    label: str = "",
) -> None
```

**Key Points:**

- 5 events instead of 24 phases (simplified from previous design)
- Label-based filtering for crew-level granularity
- `pluggy`-based hook system
- Delegated operations (git, PR) moved to plugins

### GitHub Integration (src/project_manager/)

GitHub Projects API integration:

```python
class GitHubProjectManager:
    def sync_issues_to_project(self) -> int
    def get_open_issues(self) -> list[Issue]
    def update_issue_status(self, issue_id: int, status: str) -> None
    def create_pull_request(self, ...) -> PullRequest
    def get_project_id(self) -> str
    def has_label(self, issue_number: int, label: str) -> bool
```

**Key Points:**

- Abstracted `ProjectConfig` for multi-provider support
- Status mapping for custom field names
- GraphQL and REST API support
- Project item synchronization

### Webhook Server (src/github_app/)

FastAPI-based webhook handler:

```python
@app.post("/webhook/github")
async def github_webhook(request: Request):
    payload = await request.json()
    process_github_webhook_task.delay(payload.model_dump())
```

**Key Points:**

- GitHub webhook signature verification
- Celery task offloading
- Event type filtering (issues, pull requests)

### Celery Tasks (src/celery_tasks/)

Background task processing:

```python
@app.task(bind=True, queue="feature_dev")
def kickoff_feature_dev_task(self, issue_number: int, flow_name: str):
    flow_def = get_flow_registry().get_flow(flow_name)
    flow_def.kickoff_func(kickoff_issue)
```

**Key Points:**

- Queues: `feature_dev`, `webhooks`, `monitoring`, `cleanup`
- Task tracking in database
- Exponential backoff for retries
- Periodic tasks for heartbeat and cleanup

## Data Flow

```
GitHub Issue
    ↓ (webhook)
FastAPI Server
    ↓ (async task)
Celery Worker
    ↓ (queue)
Flow Registry → FlowDef
    ↓ (kickoff)
Flow (e.g., RalphLoopFlow)
    ↓ (crew execution)
Crews (Plan, Implement, Review)
    ↓ (events)
Hooks (Git, PR, Database)
    ↓ (updates)
GitHub Projects / Database
```

## Workflow Execution: Ralph Flow

Ralph flow implements feature development with per-story commits:

```python
@start()
def setup(self):
    """Initialize worktree and discover AGENTS.md."""
    self._emit(FlowEvent.FLOW_STARTED, label="ralph")

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
        self._commit()
        self._push()
        self._emit(FlowEvent.STORY_COMPLETED, result=story, label=str(story.id))
```

**Key Points:**

- Worktree for isolated execution
- AGENTS.md discovery for build/test commands
- Per-story commits and pushes
- Git operations delegated to gitcore module
- Hook system for PR creation and merging

## Configuration

### Environment Variables

```bash
# LLM
OPENAI_API_KEY=sk-...

# Database
DATABASE_URL=postgresql://user:pass@localhost/polycode

# Redis (Celery)
REDIS_HOST=localhost
REDIS_PORT=6379

# GitHub
GITHUB_TOKEN=ghp_...
REPO_OWNER=xeroc
REPO_NAME=demo
PROJECT_IDENTIFIER=1

# Status mappings
STATUS_TODO="Todo"
STATUS_READY="Ready"
STATUS_IN_PROGRESS="In progress"
STATUS_DONE="Done"

# Webhook
GITHUB_WEBHOOK_SECRET=secret

# Label prefix
FLOW_LABEL_PREFIX=polycode:

# Default flow
DEFAULT_FLOW=ralph
```

### pyproject.toml Scripts

```toml
[project.scripts]
polycode = "cli.main:app"
example = "ralph:example"
```

## Best Practices

### Flow Development

1. **Use FlowDef pattern** - Define flows with clear labels and kickoff functions
2. **Keep state minimal** - Only store what's needed for downstream tasks
3. **Emit events** - Use FlowEvent at key lifecycle points
4. **Handle failures** - Always catch and emit FLOW_ERROR

### Crew Development

1. **Extend PolycodeCrew** - Auto-emit CREW_FINISHED events
2. **Set crew_label** - For hook filtering
3. **YAML config** - Keep agents/tasks in YAML
4. **Type annotations** - Use `# type: ignore[index]` for config access

### Module Development

1. **Implement protocol** - Satisfy PolycodeModule interface
2. **Register models** - Use RegisteredBase for auto-registration
3. **Define dependencies** - Use `dependencies` class var for load order
4. **Implement hooks** - Use `@hookimpl` decorator

## Extension Points

### Adding a New Flow

1. Create `src/flows/my_flow/flow.py` with flow class
2. Create `src/flows/my_flow/module.py` with module class
3. Register in `bootstrap.py`: `module_registry.register_builtin(MyFlowModule)`
4. Define labels in GitHub that flow handles

### Adding a New Module

1. Create `src/my_module/persistence.py` with models
2. Create `src/my_module/hooks.py` with hook implementations
3. Create `src/my_module/module.py` implementing PolycodeModule
4. Register in `bootstrap.py`

### Adding Custom Crews

1. Create `src/crews/my_crew/` directory
2. Add `config/agents.yaml` and `config/tasks.yaml`
3. Create crew class with `@CrewBase` decorator
4. Register agents and tasks using decorators

## Future Enhancements

1. **Flow chaining** - One flow triggers another
2. **Dynamic flow loading** - Load flows from external packages
3. **Advanced hook filtering** - Regex/glob pattern matching
4. **Flow versioning** - Multiple versions per flow
5. **Real-time monitoring** - WebSocket-based flow status updates

## References

- [CrewAI Documentation](https://docs.crewai.com/)
- [CrewAI Concepts: Flows](https://docs.crewai.com/en/concepts/flows)
- [CrewAI Quickstart](https://docs.crewai.com/en/quickstart)
- [PLUGIN.md](./PLUGIN.md) - Plugin architecture details
- [FLOWS.md](./FLOWS.md) - Flow system details
- [HOOK_ARCHITECTURE.md](./HOOK_ARCHITECTURE.md) - Hook system details
- [CELERY_README.md](./CELERY_README.md) - Celery integration details
