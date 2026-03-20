# Polycode

**The self-hosted, extensible GitHub bot that automates your software development workflows using AI agents.**

---

## The Problem

AI coding tools like Devin are powerful — but they're black boxes. They're SaaS-only, they speak a chat interface, and you can't customize how they work. For teams that want real automation without handing over their codebase to a third party, there's no good option.

---

## What Polycode Is

Polycode is a self-hosted GitHub App that triggers AI agent workflows directly from GitHub issues. It integrates with GitHub Projects to track issue status automatically. Label an issue, and your bot picks it up — plans, implements, commits, and opens a pull request.

No new chat interface. No vendor lock-in. No black box. Just GitHub, your infra, and your workflows.

---

## What's Built Today ✅

### Core Infrastructure

- **GitHub App Integration** — Webhook-driven event handling for issues, labels, and PRs
- **Project Manager Abstraction** — Provider-agnostic interface (currently GitHub Projects V2, extensible to GitLab, Jira)
- **Flow State Management** — Single-flight execution with automatic queueing and sequential processing
- **Async Task Processing** — Celery + Redis for reliable background job execution
- **PostgreSQL Persistence** — Storing flow state, issue mappings, and execution history

### Working Workflows

#### Ralph Flow (`ralph`)

Fast, iterative implementation with automatic verification loops.

1. **Plan** — Decompose issue into ordered user stories
2. **Implement** — Write code, story by story
3. **Ralph Loop** — Iterative implementation with verification:
   - Implement current story
   - Run tests to verify changes
   - If tests fail, retry with error context (max 3 iterations)
   - If tests pass, commit story and move to next
4. **Verify Build** — Final build and test verification
5. **Push & PR** — Push changes and create pull request

**Safety features:**

- Per-story commits for atomic changes
- 3-iteration limit prevents runaway processes
- Error context passed to retries for smarter recovery

#### Feature Dev Flow (`feature-dev`)

Comprehensive workflow for larger features — planning, implementation, testing, and code review in sequence.

1. **Plan** — Decompose task into ordered user stories
2. **Implement** — Implement each story with tests
3. **Push** — Push changes to repository
4. **Create PR** — Create pull request
5. **Review** — Code review with feedback

### Webhook-Driven Execution

```
GitHub Issue Event → Add to Project → Check if Ready
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

Only one flow runs at a time (single-flight execution). When a webhook receives an event:

- If a flow is running → Issue is queued (added to project, marked Ready)
- If no flow is running → Flow starts immediately
- When flow completes → Automatically triggers next Ready issue

---

## What's Coming Soon 🚧

### Configuration System (Immediate Next)

The `.polycode/polycode.yml` config will map GitHub labels to workflows:

```yaml
version: 1
flows:
  hotfix:
    label: hotfix
    source: ./flows/hotfix.py # bring your own

  ralph:
    label: ralph
    source: polycode/ralph # built-in flow

  deploy-check:
    label: deploy-check
    source: github:acme-org/polycode-flows/deploy # from any GitHub repo
```

The `source` field is a power move: point it at a local file, a built-in flow, or any GitHub repo. Teams can publish reusable workflow libraries. You can share flows across your entire organization.

### Docker Deployment

Self-hosting in one command:

```bash
docker run \
  -e GITHUB_APP_ID=... \
  -e PRIVATE_KEY=... \
  -e DATABASE_URL=... \
  ghcr.io/polycode/polycode
```

Your code stays on your infra. Your workflows run on your terms.

### Additional Providers

The project manager abstraction is designed to support:

- GitLab Projects API
- Jira REST API
- Azure DevOps Boards

Plug in a new provider by implementing the `ProjectManager` interface.

---

## Why Not Devin?

|                  | Devin        | Polycode                            |
| ---------------- | ------------ | ----------------------------------- |
| Hosting          | SaaS only    | Self-hosted                         |
| Workflows        | Black box    | Fully customizable                  |
| Interface        | Chat / Slack | GitHub-native                       |
| Workflow sharing | None         | Import from any GitHub repo         |
| Code visibility  | Opaque       | Full audit trail, per-story commits |
| Data ownership   | Vendor       | You                                 |
| Project tracking | None         | GitHub Projects integration         |

Devin is built for demos. Polycode is built for teams that want automation they can trust, inspect, and extend.

---

## The Extensibility Model

Polycode is built on [CrewAI](https://docs.crewai.com/), an open multi-agent framework. Every workflow is just a Python file. Agents have access to standard tools — read/write files, run shell commands, explore directories, load project context — and you can add your own.

This means:

- **Teams** can write workflows that match their exact process
- **Organizations** can maintain a shared `polycode-flows` repo everyone pulls from
- **The community** can publish and share flows openly

The goal is an ecosystem of composable agent workflows — not one tool that tries to do everything.

---

## Project Architecture

```
┌─────────────────────────────────────────────┐
│         GitHub Webhook Events            │
└─────────────┬─────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│      FastAPI Webhook Server            │
├─────────────────────────────────────────────┤
│  - Validate webhook signatures          │
│  - Parse issue events                 │
│  - Queue issues to project            │
└─────────────┬─────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│      Project Manager (GitHub V2)       │
├─────────────────────────────────────────────┤
│  - Add issues to project              │
│  - Update status (Todo/Ready/Done)   │
│  - Sync issues to project board        │
└─────────────┬─────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│      Flow State Manager                │
├─────────────────────────────────────────────┤
│  - Single-flight execution            │
│  - Queue ready issues               │
│  - Trigger next on completion       │
└─────────────┬─────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│      Celery Task Queue                │
├─────────────────────────────────────────────┤
│  - Async flow execution             │
│  - Retry logic                     │
│  - Worker pools                    │
└─────────────┬─────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│      CrewAI Workflows                 │
├─────────────────────────────────────────────┤
│  - Ralph Flow (fast iterative)      │
│  - Feature Dev Flow (comprehensive)   │
└─────────────┬─────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────────┐
│      PostgreSQL                       │
├─────────────────────────────────────────────┤
│  - Flow state persistence            │
│  - Execution history                │
│  - Label mappings                  │
└─────────────────────────────────────────┘
```

---

## Getting Started

### Local Development

```bash
# 1. Install dependencies
uv sync

# 2. Configure environment
cp .env.example .env
# Edit .env with your GITHUB_TOKEN, DATABASE_URL, etc.

# 3. Run a flow locally
uv run ralph                # Run Ralph flow (interactive)
uv run example               # Run feature dev example

# 4. Start webhook server
uv run uvicorn github_app.app:app --reload
```

### Testing Webhook Integration

```bash
# Terminal 1: Start webhook server
export GITHUB_TOKEN=ghp_xxx
export REPO_OWNER=xeroc
export REPO_NAME=demo
export PROJECT_IDENTIFIER=1
python -m project_manager.cli webhook

# Terminal 2: Check status
python -m project_manager.cli status

# Terminal 3: Manual trigger
curl -X POST http://localhost:8000/trigger?issue_number=42
```

---

## Development Commands

```bash
# Dependency management
uv sync                   # Install dependencies
uv add <package>          # Add dependency

# Linting & type checking
uv run ruff check .                    # Lint all files
uv run ruff check --fix .              # Auto-fix lint errors
uv run ruff format .                   # Format code
uv run pyright                         # Type check (via pre-commit)

# Testing
uv run pytest                            # Run all tests
uv run pytest tests/test_ralph.py         # Run single test file
uv run pytest -k "label"               # Run tests matching pattern

# Run application
uv run python -m project_manager.cli    # CLI entry point
uv run uvicorn github_app.app:app       # FastAPI webhook server
```

---

## Status

Polycode is in active development. The following features are **working**:

- ✅ Ralph Flow (iterative implementation with verification)
- ✅ Feature Dev Flow (comprehensive feature development)
- ✅ GitHub App integration (webhooks, issue events)
- ✅ Project Manager abstraction (GitHub Projects V2)
- ✅ Flow state management (single-flight execution)
- ✅ Celery + Redis async processing
- ✅ PostgreSQL persistence

**Immediate next milestones:**

- 🚧 `.polycode/polycode.yml` config system for label-to-flow mapping
- 🚧 Docker deployment with compose file
- 🚧 CLI tool for `polycode init` and `polycode run`
- 🚧 Documentation for writing custom workflows

If you want to try it early or contribute, open an issue or reach out directly.

---

## Tech Stack

- **Python 3.13+** with `uv` package manager
- **CrewAI** — multi-agent orchestration framework
- **GitHub Apps** — webhook-driven automation
- **GitHub Projects V2** — project board integration via GraphQL
- **Celery + Redis** — async task processing
- **PostgreSQL** — persistence layer
- **FastAPI** — webhook server
- **Pydantic** — data validation

---

## Links

- **Homepage**: [polycod.ing](https://polycod.ing)
- **Github**: [xeroc/polycode](https://github.com/xeroc/polycode)
- **Github App**: [apps/polycode-agent/](https://github.com/apps/polycode-agent/)

---

_MIT License_
