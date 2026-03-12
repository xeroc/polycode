# Project Manager

Abstraction layer for project management providers (GitHub, GitLab, Jira, etc.) with **event-driven webhook support**.

## Overview

The Project Manager package provides a provider-agnostic interface for managing issues and project boards. It supports both polling and webhook-driven architectures, currently with GitHub Projects V2 support.

## Architecture

```
┌─────────────────────────────────────────────┐
│          ProjectManager (ABC)               │
├─────────────────────────────────────────────┤
│  - get_open_issues()                        │
│  - get_project_items()                      │
│  - add_issue_to_project()                   │
│  - update_issue_status()                    │
│  - add_comment()                            │
│  - sync_issues_to_project()                 │
└─────────────────────────────────────────────┘
                    ▲
                    │
        ┌───────────┴───────────┐
        │                       │
┌───────────────┐     ┌─────────────────┐
│ GitHub        │     │ Future: GitLab, │
│ ProjectManager│     │ Jira, etc.      │
└───────────────┘     └─────────────────┘
        │
        │
┌───────┴────────┐
│  FlowRunner    │
├────────────────┤
│ - trigger_flow │
│ - complete_flow│
│ - is_running   │
└───────┬────────┘
        │
        │
┌───────┴──────────────┐
│  Webhook (FastAPI)   │
├──────────────────────┤
│ POST /webhook/github │
│ POST /trigger        │
│ GET  /health         │
└──────────────────────┘
```

## Event-Driven Architecture

### Flow Execution Model

```
Webhook Event → Add to Project → Check if Ready
                                    ↓
                              If Ready & Not Running
                                    ↓
                          Start Flow → Mark In Progress
                                    ↓
                              Execute Callback
                                    ↓
                          Complete Flow → Check Next
                                    ↓
                          Trigger Next Ready Issue
```

### Single-Flight Execution

Only **one flow runs at a time**. When a webhook receives an event:

- If a flow is running → Issue is queued (added to project, marked Ready)
- If no flow is running → Flow starts immediately
- When flow completes → Automatically triggers next Ready issue

This ensures:

- No concurrent flow execution
- Predictable resource usage
- Ordered processing of issues

## Usage

### Configuration via Environment Variables

```bash
# Required
export PROJECT_PROVIDER=github
export REPO_OWNER=xeroc
export REPO_NAME=demo
export PROJECT_IDENTIFIER=1
export GITHUB_TOKEN=ghp_xxx

# Webhook (optional)
export GITHUB_WEBHOOK_SECRET=your-secret

# Optional: Custom status mappings
export STATUS_TODO="Todo"
export STATUS_READY="Ready"
export STATUS_IN_PROGRESS="In progress"
export STATUS_REVIEWING="Reviewing"
export STATUS_DONE="Done"
export STATUS_BLOCKED="Blocked"
```

### Webhook Mode (Recommended)

Start the webhook server:

```bash
python -m project_manager.cli webhook

# Custom host/port
python -m project_manager.cli webhook --host 0.0.0.0 --port 8080

# With secret
python -m project_manager.cli webhook --secret your-secret
```

**Endpoints:**

- `POST /webhook/github` - GitHub webhook endpoint
- `POST /trigger?issue_number=42` - Manual trigger (optional issue number)
- `GET /health` - Health check with flow status

**Configure GitHub Webhook:**

1. Go to repository Settings → Webhooks
2. Add webhook: `http://your-server:8000/webhook/github`
3. Content type: `application/json`
4. Secret: Match `GITHUB_WEBHOOK_SECRET`
5. Events: Select "Issues"

**Flow:**

1. Issue opened → GitHub sends webhook
2. Issue added to project
3. If ready and no flow running → Flow starts
4. Flow completes → Next ready issue processed

### Polling Mode (Legacy)

```bash
# Continuous polling
python -m project_manager.cli watch

# One-time run
python -m project_manager.cli watch --once

# Custom poll interval
python -m project_manager.cli watch --interval 60
```

### Other Commands

```bash
# Sync issues
python -m project_manager.cli sync

# List items
python -m project_manager.cli list

# Check flow status
python -m project_manager.cli status
```

### Programmatic Usage

#### Webhook Server

```python
from project_manager import GitHubProjectManager, FlowRunner, FlowStateManager
from project_manager.webhook import create_webhook_app
import uvicorn

config = ProjectConfig(
    provider="github",
    repo_owner="xeroc",
    repo_name="demo",
    project_identifier="1",
)

manager = GitHubProjectManager(config)
state_manager = FlowStateManager()

def on_issue_ready(item):
    print(f"Processing: {item.title}")
    # Your flow logic here

flow_runner = FlowRunner(
    manager=manager,
    state_manager=state_manager,
    on_issue_ready=on_issue_ready,
)

app = create_webhook_app(flow_runner, webhook_secret="secret")
uvicorn.run(app, host="0.0.0.0", port=8000)
```

#### Manual Flow Control

```python
from project_manager import GitHubProjectManager, FlowRunner, FlowStateManager
from project_manager.types import ProjectConfig, IssueStatus

config = ProjectConfig(
    provider="github",
    repo_owner="xeroc",
    repo_name="demo",
    project_identifier="1",
)

manager = GitHubProjectManager(config)
state_manager = FlowStateManager()

def on_issue_ready(item):
    print(f"Processing issue #{item.issue_number}")
    # Your flow logic
    # When done, call: flow_runner.complete_flow(item.issue_number)

flow_runner = FlowRunner(
    manager=manager,
    state_manager=state_manager,
    on_issue_ready=on_issue_ready,
)

# Trigger next ready issue
flow_runner.trigger_flow()

# Trigger specific issue
flow_runner.trigger_flow(issue_number=42)

# Check if running
if flow_runner.is_flow_running():
    print("Flow already in progress")

# Mark complete (usually called by on_issue_ready callback)
flow_runner.complete_flow(issue_number=42, success=True)
```

## Components

### Types (`types.py`)

- **Issue**: Generic issue representation
- **ProjectItem**: Generic project item representation
- **StatusMapping**: Maps standardized statuses to provider-specific values
- **ProjectConfig**: Configuration for project manager

### Base Class (`base.py`)

Abstract base class defining the provider interface.

### GitHub Implementation (`github.py`)

GitHub Projects V2 implementation using GraphQL API.

### Flow State (`flow_state.py`)

File-based state management for tracking running flows.

### Flow Runner (`flow_runner.py`)

Manages flow execution with single-flight guarantee.

### Webhook (`webhook.py`)

FastAPI webhook server for GitHub events.

### CLI (`cli.py`)

Command-line tools for project management.

## Webhook Flow Example

```bash
# Terminal 1: Start webhook server
export REPO_OWNER=xeroc
export REPO_NAME=demo
export PROJECT_IDENTIFIER=1
export GITHUB_TOKEN=ghp_xxx
export GITHUB_WEBHOOK_SECRET=mysecret

python -m project_manager.cli webhook --verbose

# Terminal 2: Check status
python -m project_manager.cli status

# Terminal 3: Manual trigger (optional)
curl -X POST http://localhost:8000/trigger
curl -X POST http://localhost:8000/trigger?issue_number=42
```

## Integration with feature_dev

The webhook automatically integrates with `feature_dev` flow:

```python
# In webhook callback
def on_issue_ready(item):
    from feature_dev import kickoff
    from feature_dev.types import KickoffIssue

    issue = KickoffIssue(
        id=item.issue_number,
        title=item.title,
        body=item.body or "",
    )

    kickoff(issue)  # This runs feature development flow
```

When flow completes, it automatically triggers the next ready issue.

## API Reference

### FlowRunner

```python
runner = FlowRunner(
    manager: ProjectManager,
    state_manager: FlowStateManager | None = None,
    on_issue_ready: Callable[[ProjectItem], None] | None = None,
)

runner.is_flow_running() -> bool
runner.trigger_flow(issue_number: int | None = None) -> bool
runner.complete_flow(issue_number: int, success: bool = True) -> None
```

### FlowStateManager

```python
state = FlowStateManager(state_dir: str | None = None)

state.is_flow_running() -> bool
state.get_running_flow() -> FlowState | None
state.start_flow(issue_number: int) -> FlowState
state.complete_flow(issue_number: int, success: bool = True) -> None
state.clear_state() -> None
```

### Webhook Endpoints

**POST /webhook/github**

- GitHub webhook endpoint
- Validates signature
- Handles issue events (opened, reopened, labeled)
- Returns: `{"status": "triggered"|"queued"|"ignored", ...}`

**POST /trigger**

- Manual trigger
- Query params: `issue_number` (optional)
- Returns: `{"status": "triggered"|"already_running", ...}`

**GET /health**

- Health check
- Returns: `{"status": "healthy", "flow_running": bool, "current_flow": {...}|null}`

## Future Enhancements

- [ ] GitLab support
- [ ] Jira support
- [ ] Database-backed state management (PostgreSQL)
- [ ] Multiple concurrent flows with resource limits
- [ ] Flow priority queue
- [ ] Retry failed flows
- [ ] Flow metrics and observability
- [ ] Issue assignment and labeling
- [ ] Multi-project support

## Extending to New Providers

To add a new provider (e.g., GitLab):

1. Create `gitlab.py` implementing `ProjectManager`
2. Implement all abstract methods
3. Register in `cli.py`'s `create_manager_from_env()`
4. Add provider-specific configuration as needed

Example:

```python
# gitlab.py
from .base import ProjectManager
from .types import Issue, ProjectItem, ProjectConfig

class GitLabProjectManager(ProjectManager):
    def __init__(self, config: ProjectConfig):
        super().__init__(config)
        # Initialize GitLab client

    def get_open_issues(self) -> list[Issue]:
        # GitLab-specific implementation
        pass

    # ... implement other abstract methods
```

## Migration Guide

### From github_issues/main.py

**Old (Polling):**

```python
# Hard-coded configuration
REPO_OWNER = "xeroc"
REPO_NAME = "demo"
PROJECT_NUMBER = 1

while True:
    run_cycle()
    time.sleep(300)
```

**New (Webhook):**

```bash
# Environment variables
export REPO_OWNER=xeroc
export REPO_NAME=demo
export PROJECT_IDENTIFIER=1

# Start webhook server
python -m project_manager.cli webhook
```

**New (Polling):**

```bash
python -m project_manager.cli watch
```

### From feature_dev/github_status.py

**Old:**

```python
from github import Github
from github_issues.github_project import GitHubProjectsClient

class ProjectStatusManager:
    def __init__(self):
        self.github_client = Github(token)
        self.projects_client = GitHubProjectsClient(token, REPO_NAME)
```

**New:**

```python
from project_manager import GitHubProjectManager

class ProjectStatusManager:
    def __init__(self):
        config = ProjectConfig(
            provider="github",
            repo_owner=repo_owner,
            repo_name=repo_name,
            project_identifier=project_identifier,
        )
        self.manager = GitHubProjectManager(config)
```

┌─────────────────────────────────────────────┐
│ ProjectManager (ABC) │
├─────────────────────────────────────────────┤
│ - get_open_issues() │
│ - get_project_items() │
│ - add_issue_to_project() │
│ - update_issue_status() │
│ - add_comment() │
│ - sync_issues_to_project() │
└─────────────────────────────────────────────┘
▲
│
┌───────────┴───────────┐
│ │
┌───────────────┐ ┌─────────────────┐
│ GitHub │ │ Future: GitLab, │
│ ProjectManager│ │ Jira, etc. │
└───────────────┘ └─────────────────┘

````

## Usage

### Configuration via Environment Variables

```bash
# Required
export PROJECT_PROVIDER=github
export REPO_OWNER=xeroc
export REPO_NAME=demo
export PROJECT_IDENTIFIER=1
export GITHUB_TOKEN=ghp_xxx

# Optional: Custom status mappings
export STATUS_TODO="Todo"
export STATUS_READY="Ready"
export STATUS_IN_PROGRESS="In progress"
export STATUS_REVIEWING="Reviewing"
export STATUS_DONE="Done"
export STATUS_BLOCKED="Blocked"
````

### CLI Commands

#### Watch Repository

Poll for issues and process them automatically:

```bash
# With environment variables configured
python -m project_manager.cli watch

# One-time run
python -m project_manager.cli watch --once

# Custom poll interval (default: 300 seconds)
python -m project_manager.cli watch --interval 60

# Verbose logging
python -m project_manager.cli watch --verbose
```

#### Sync Issues

Sync all open issues to the project board:

```bash
python -m project_manager.cli sync
```

#### List Project Items

List all items in the project:

```bash
python -m project_manager.cli list
```

### Programmatic Usage

```python
from project_manager import GitHubProjectManager
from project_manager.types import ProjectConfig, IssueStatus

# Create manager
config = ProjectConfig(
    provider="github",
    repo_owner="xeroc",
    repo_name="demo",
    project_identifier="1",
)
manager = GitHubProjectManager(config)

# Get all open issues
issues = manager.get_open_issues()

# Get project items
items = manager.get_project_items()

# Update status
manager.update_issue_status(
    issue_number=42,
    status=manager.config.status_mapping.to_provider_status(IssueStatus.IN_PROGRESS)
)

# Add comment
manager.add_comment(issue_number=42, comment="Working on this...")

# Sync issues to project
added = manager.sync_issues_to_project()
```

## Components

### Types (`types.py`)

- **Issue**: Generic issue representation
- **ProjectItem**: Generic project item representation
- **StatusMapping**: Maps standardized statuses to provider-specific values
- **ProjectConfig**: Configuration for project manager

### Base Class (`base.py`)

Abstract base class defining the provider interface.

### GitHub Implementation (`github.py`)

GitHub Projects V2 implementation using GraphQL API.

### CLI (`cli.py`)

Command-line tools for project management.

## Future Enhancements

- [ ] GitLab support
- [ ] Jira support
- [ ] Webhook endpoint for real-time notifications
- [ ] FastAPI integration for webhook server
- [ ] Database-backed state management
- [ ] Issue assignment and labeling
- [ ] Multi-project support

## Extending to New Providers

To add a new provider (e.g., GitLab):

1. Create `gitlab.py` implementing `ProjectManager`
2. Implement all abstract methods
3. Register in `cli.py`'s `create_manager_from_env()`
4. Add provider-specific configuration as needed

Example:

```python
# gitlab.py
from .base import ProjectManager
from .types import Issue, ProjectItem, ProjectConfig

class GitLabProjectManager(ProjectManager):
    def __init__(self, config: ProjectConfig):
        super().__init__(config)
        # Initialize GitLab client

    def get_open_issues(self) -> list[Issue]:
        # GitLab-specific implementation
        pass

    # ... implement other abstract methods
```

## Migration Guide

### From github_issues/main.py

Old:

```python
# Hard-coded configuration
REPO_OWNER = "xeroc"
REPO_NAME = "demo"
PROJECT_NUMBER = 1
```

New:

```bash
# Environment variables
export REPO_OWNER=xeroc
export REPO_NAME=demo
export PROJECT_IDENTIFIER=1
```

### From feature_dev/github_status.py

Old:

```python
from github import Github
from github_issues.github_project import GitHubProjectsClient

class ProjectStatusManager:
    def __init__(self):
        self.github_client = Github(token)
        self.projects_client = GitHubProjectsClient(token, REPO_NAME)
```

New:

```python
from project_manager import GitHubProjectManager

class ProjectStatusManager:
    def __init__(self):
        config = ProjectConfig(
            provider="github",
            repo_owner=repo_owner,
            repo_name=repo_name,
            project_identifier=project_identifier,
        )
        self.manager = GitHubProjectManager(config)
```
