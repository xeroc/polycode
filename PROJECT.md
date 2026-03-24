# Polycode

**The self-hosted, extensible GitHub bot that automates software development with AI agents.**

---

## The Problem

AI coding tools are powerful — but they're black boxes. SaaS-only. Opaque. Inflexible. Teams that want real automation without handing over their codebase to a third party have no good options.

---

## What Polycode Does

**Label an issue, ship a feature.**

Polycode is a self-hosted GitHub App that triggers AI agent workflows directly from GitHub issues. Add a label like `polycode:implement`, and your bot picks it up — plans, implements, commits, and opens a pull request. All tracked in GitHub Projects.

```
GitHub Issue → Add Label → Flow Starts → Crew Plans & Implements → PR Created → Merged
```

No chat interface. No vendor lock-in. Just GitHub, your infrastructure, and workflows you control.

---

## Key Features

### 🏷️ Label-Driven Workflows

GitHub labels trigger different flows:

| Label                   | Flow              | What It Does                           |
| ----------------------- | ----------------- | -------------------------------------- |
| `polycode:implement`    | Ralph Flow        | Plan → Implement → Verify → PR → Merge |
| `polycode:review`       | Review Flow       | Code review with automated feedback    |
| `polycode:deploy-check` | Deploy Check Flow | Pre-deployment validation              |

Custom flows match any label pattern you define.

### 🔌 Plugin Architecture

Extend Polycode with Python modules:

- **Built-in modules**: Ralph (feature dev), Retrospectives
- **Community flows**: Import from any GitHub repo
- **Your flows**: Write custom workflows for your team's process

```python
# .polycode/polycode.yml
flows:
  ralph:
    label: implement
    source: polycode/ralph  # built-in

  deploy-check:
    label: deploy-check
    source: github:acme-org/polycode-flows/deploy  # from GitHub
```

### 🤖 AI-Powered Crews

Built on CrewAI — teams of specialized AI agents:

| Crew            | Purpose                            |
| --------------- | ---------------------------------- |
| **Plan Crew**   | Decompose issues into user stories |
| **Implement**   | Write code, story by story         |
| **Review Crew** | Code review with feedback loops    |
| **Verify Crew** | Run tests, verify builds           |

Each crew uses tools to read/write files, run commands, and explore your codebase.

### 🔗 GitHub Projects Integration

Automatic status tracking:

```
Todo → Ready → In Progress → Reviewing → Done
```

- Issues sync automatically
- Status updates at each flow phase
- Full visibility in GitHub Projects board

### 🪝 Extensible Hook System

5 lifecycle events (simplified from 24):

| Event             | When It Fires            | Use Case                       |
| ----------------- | ------------------------ | ------------------------------ |
| `FLOW_STARTED`    | Flow begins              | Post comment, lock issue       |
| `CREW_FINISHED`   | Crew completes work      | Log output, update status      |
| `STORY_COMPLETED` | Single story implemented | Commit, push, update checklist |
| `FLOW_FINISHED`   | All stories done         | Create PR, merge, cleanup      |
| `FLOW_ERROR`      | Unhandled exception      | Alert, generate retro          |

Hooks are Python functions — any module can register them.

---

## How It Works

### Architecture

```
GitHub Webhook
     ↓
FastAPI Server → Validate & Queue
     ↓
Celery Workers → Background Processing
     ↓
Flow Registry → Match Label to Flow
     ↓
CrewAI Agents → Plan, Implement, Verify
     ↓
Hooks → Commit, Push, PR, Merge
     ↓
GitHub Projects → Status Updates
     ↓
PostgreSQL → State Persistence
```

### Ralph Flow (Feature Development)

The flagship workflow for iterative feature development:

```
1. PLAN
   - Parse issue
   - Generate ordered user stories
   - Discover build/test commands from AGENTS.md

2. IMPLEMENT (per story)
   - Write code
   - Run tests
   - If fail → retry with error context (max 3x)
   - If pass → commit & push

3. VERIFY
   - Full build
   - Full test suite

4. FINALIZE
   - Create PR
   - Auto-merge (if approved)
   - Update checklist
   - Cleanup worktree
```

**Safety features:**

- Per-story commits (atomic, traceable)
- 3-iteration limit (prevents runaway loops)
- Isolated worktrees (no conflicts)
- Error context passed to retries

---

## Technology Stack

| Layer        | Technology                         |
| ------------ | ---------------------------------- |
| **Agent**    | CrewAI (multi-agent orchestration) |
| **LLM**      | OpenAI GPT-4, Anthropic Claude     |
| **Backend**  | Python 3.13, FastAPI, Pydantic     |
| **Queue**    | Celery + Redis                     |
| **Database** | PostgreSQL                         |
| **Git**      | Git worktrees for isolation        |
| **CLI**      | Typer                              |

---

## CLI Commands

```bash
# Webhook server
polycode server start --host 0.0.0.0 --port 8080

# Background workers
polycode worker start --queue feature_dev

# Execute flows
polycode flow list
polycode flow run ralph --issue 42

# Manage projects
polycode project sync    # Sync issues to project
polycode project list    # List all project items
polycode project status  # Check flow status

# Database operations
polycode db status       # Show DB status
polycode db migrate      # Run migrations
```

---

## Quick Start

### 1. Install

```bash
cd apps/polycode
uv sync
```

### 2. Configure

```bash
# .env
GITHUB_TOKEN=ghp_...
DATABASE_URL=postgresql://...
REDIS_HOST=localhost
OPENAI_API_KEY=sk-...
```

### 3. Run

```bash
# Terminal 1: Webhook server
polycode server start

# Terminal 2: Background workers
polycode worker start

# Terminal 3: Trigger flow
polycode flow run ralph --issue 42
```

---

## Self-Hosting

### Docker

```bash
docker run \
  -e GITHUB_APP_ID=... \
  -e PRIVATE_KEY=... \
  -e DATABASE_URL=... \
  ghcr.io/polycode/polycode
```

Your code stays on your infrastructure. Your workflows run on your terms.

---

## Comparison

|                      | Devin        | Polycode                            |
| -------------------- | ------------ | ----------------------------------- |
| **Hosting**          | SaaS only    | Self-hosted                         |
| **Workflows**        | Black box    | Fully customizable                  |
| **Interface**        | Chat / Slack | GitHub-native                       |
| **Workflow sharing** | None         | Import from any GitHub repo         |
| **Code visibility**  | Opaque       | Full audit trail, per-story commits |
| **Data ownership**   | Vendor       | You                                 |
| **Project tracking** | None         | GitHub Projects integration         |
| **Extensibility**    | None         | Plugin architecture                 |

Devin is built for demos. Polycode is built for teams.

---

## Extensibility

### Create a Custom Flow

1. **Define the flow** (`src/flows/my_flow/flow.py`):

```python
from flows.base import FlowIssueManagement, KickoffIssue

class MyFlow(FlowIssueManagement[MyState]):
    @start()
    def setup(self):
        self._emit(FlowEvent.FLOW_STARTED, label="my-flow")

    @listen(setup)
    def execute(self):
        # Your logic here
        pass

def kickoff(issue: KickoffIssue):
    MyFlow().kickoff(inputs={...})
```

1. **Register the module** (`src/flows/my_flow/module.py`):

```python
class MyFlowModule:
    name = "my-flow"

    @classmethod
    def get_flows(cls):
        return [FlowDef(
            name="my-flow",
            kickoff_func=kickoff,
            supported_labels=["my-action"],
        )]
```

1. **Add label in GitHub**: `polycode:my-action`

### Create a Plugin Hook

```python
from modules.hooks import FlowEvent, hookimpl

class MyHooks:
    @hookimpl
    def on_flow_event(self, event, flow_id, state, result=None, label=""):
        if event == FlowEvent.STORY_COMPLETED:
            # Custom action after each story
            pass
```

---

## Roadmap

### Implemented ✅

- GitHub App integration (webhooks, issue events)
- GitHub Projects V2 integration (status tracking)
- Ralph Flow (iterative feature development)
- Plugin architecture (modules, hooks, flows)
- Label-driven workflow triggering
- Celery + Redis async processing
- PostgreSQL persistence
- CLI with all core commands
- 5-event hook system (simplified from 24)
- Per-story commits and pushes

### Coming Soon 🚧

- `.polycode/polycode.yml` config system
- Docker Compose deployment
- Flow marketplace (shareable workflows)
- GitLab Projects API support
- Jira integration
- Real-time WebSocket updates
- Flow versioning

---

## Project Links

- **Homepage**: [polycod.ing](https://polycod.ing)
- **GitHub**: [xeroc/polycode](https://github.com/xeroc/polycode)
- **GitHub App**: [apps/polycode-agent/](https://github.com/apps/polycode-agent/)

---

MIT License
