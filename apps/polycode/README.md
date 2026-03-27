# Polycode

Multi-agent software development automation using CrewAI. GitHub App integration for webhook-driven workflows across multiple repositories.

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [Architecture](#architecture)
- [Environment Variables](#environment-variables)
- [Available Scripts](#available-scripts)
- [CLI Commands](#cli-commands)
- [Testing](#testing)
- [Workflows](#workflows)
- [GitHub App Integration](#github-app-integration)
- [Docker Deployment](#docker-deployment)
- [Troubleshooting](#troubleshooting)

---

## Overview

Polycode automates software development tasks using AI-powered multi-agent workflows. It integrates as a GitHub App to provide seamless automation triggered by issue labels.

### Key Features

- **Multi-agent CrewAI workflows** - Plan, implement, review, test, and verify code
- **GitHub App integration** - Webhook-driven automation for multi-repo support
- **Label-to-flow mapping** - Trigger workflows by adding labels to issues
- **Iterative development** - Ralph Loop with automatic verification and retry
- **Context+ integration** - Semantic code intelligence via MCP/Ollama

### Available Workflows

| Workflow | Label     | Description                                               |
| -------- | --------- | --------------------------------------------------------- |
| Ralph    | `ralph`   | Fast iterative implementation with automated verification |
| Specify  | `specify` | Feature specification and planning workflow               |

---

## Tech Stack

- **Language**: Python 3.13+
- **Framework**: CrewAI 1.10+ (multi-agent orchestration)
- **Web Server**: FastAPI with Uvicorn
- **Database**: PostgreSQL 16+ with SQLAlchemy/SQLModel
- **Queue**: Celery with Redis
- **Package Manager**: uv
- **CLI**: Typer with Rich
- **Real-time**: Socket.IO for streaming events
- **Deployment**: Docker (includes Node.js 22, Bun, Context+)

---

## Prerequisites

- **Python 3.13+** (via pyenv, mise, or asdf)
- **uv** package manager - `curl -LsSf https://astral.sh/uv/install.sh | sh`
- **PostgreSQL 16+** (or Docker)
- **Redis** (for Celery background jobs)
- **GitHub App** credentials (for webhook integration)
- **Ollama** (optional, for Context+ semantic search)

---

## Getting Started

### 1. Clone and Install

```bash
git clone https://github.com/your-org/polycode.git
cd polycode
uv sync
```

### 2. Environment Setup

Copy the example environment file:

```bash
cp .env.example .env
```

Configure required variables (see [Environment Variables](#environment-variables)).

### 3. Database Setup

Using Docker:

```bash
docker run --name postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=polycode \
  -p 5432:5432 \
  -d postgres:16
```

Using local PostgreSQL:

```bash
# macOS
brew install postgresql@16
brew services start postgresql@16
createdb polycode

# Ubuntu
sudo apt install postgresql-16
sudo -u postgres createdb polycode
```

The database tables are auto-created on first run via SQLAlchemy.

### 4. Redis Setup

```bash
docker run --name redis -p 6379:6379 -d redis:7
```

Or locally:

```bash
# macOS
brew install redis
brew services start redis

# Ubuntu
sudo apt install redis-server
sudo systemctl start redis
```

### 5. Start Services

**Development (all services):**

```bash
# Terminal 1: FastAPI webhook server
uv run polycode server webhook --reload

# Terminal 2: Socket.IO streaming server
uv run polycode server socketio --reload

# Terminal 3: Celery worker
uv run polycode worker start --queues celery,default --loglevel=info

# Terminal 4: Flower (Celery monitoring, optional)
uv run polycode worker flower
```

**Quick test:**

```bash
uv run polycode --help
```

---

## Architecture

### Directory Structure

```
polycode/
├── src/
│   ├── cli/                    # Typer CLI commands
│   │   ├── main.py             # Entry point
│   │   ├── server.py           # Server management
│   │   ├── worker.py           # Celery worker commands
│   │   ├── flow.py             # Flow execution
│   │   ├── project.py          # GitHub project management
│   │   └── db.py               # Database utilities
│   ├── crews/                  # CrewAI crew definitions
│   │   ├── base.py             # PolycodeCrewMixin with hooks
│   │   ├── plan_crew/          # Story planning
│   │   ├── implement_crew/     # Code implementation
│   │   ├── review_crew/        # Code review
│   │   ├── test_crew/          # Test generation
│   │   ├── verify_crew/        # Build verification
│   │   ├── ralph_crew/         # Ralph loop implementation
│   │   ├── conversation_crew/  # Conversational agent
│   │   └── streaming/          # Real-time event publishing
│   ├── flows/                  # CrewAI Flow orchestration
│   │   ├── base.py             # FlowIssueManagement base
│   │   ├── protocol.py         # Flow protocol definitions
│   │   ├── ralph/              # Ralph Loop flow
│   │   └── specify/            # Specify flow
│   ├── channels/               # Real-time communication
│   │   ├── base.py             # Channel base class
│   │   ├── dispatcher.py       # Multi-channel dispatcher
│   │   ├── redis/              # Redis pub/sub channel
│   │   └── stream/             # Socket.IO streaming
│   ├── github_app/             # GitHub App integration
│   │   ├── app.py              # FastAPI webhook server
│   │   ├── auth.py             # JWT authentication
│   │   ├── webhook_handler.py  # Event processing
│   │   ├── installation_manager.py
│   │   └── label_mapper.py     # Label-to-flow mapping
│   ├── project_manager/        # GitHub project management
│   │   ├── github.py           # GitHub API client
│   │   ├── github_projects_client.py
│   │   ├── git_utils.py        # Git operations
│   │   ├── flow_runner.py      # Flow execution
│   │   └── types.py            # Pydantic models
│   ├── persistence/            # Database layer
│   │   ├── postgres.py         # SQLAlchemy models
│   │   └── config.py           # Database settings
│   ├── gitcore/                # Git worktree operations
│   ├── modules/                # Plugin hook system
│   ├── tools/                  # Custom CrewAI tools
│   │   ├── file_read_tool.py
│   │   ├── directory_read_tool.py
│   │   ├── exec_tool.py
│   │   └── agents_md_loader.py
│   ├── tasks/                  # Task templates
│   ├── glm.py                  # GLM JSON LLM wrapper
│   └── bootstrap.py            # Application bootstrap
├── task_templates/             # Custom task templates
│   ├── custom_implement.md
│   └── custom_generate_result.md
├── tests/                      # Test files
├── docs/                       # Documentation
├── Dockerfile
├── entrypoint.sh
├── Makefile
└── pyproject.toml
```

### Request Lifecycle

```
GitHub Webhook → FastAPI /webhook/github → LabelMapper → Celery Task
                                                        ↓
                                             FlowRunner.kickoff()
                                                        ↓
                                             RalphLoopFlow (CrewAI Flow)
                                                        ↓
                                             PlanCrew → RalphCrew → VerifyCrew
                                                        ↓
                                             Hook Events (git commit, PR create)
```

### Flow Event System

The hook system enables modular event handling:

| Event             | Emitted By     | Hook Handler           |
| ----------------- | -------------- | ---------------------- |
| `FLOW_STARTED`    | Flow setup     | Initialize resources   |
| `STORIES_PLANNED` | PlanCrew       | Create checklist items |
| `STORY_COMPLETED` | Implement step | Commit + push code     |
| `CREW_FINISHED`   | Any crew       | Log, metrics           |
| `FLOW_FINISHED`   | Flow complete  | Create PR, cleanup     |
| `CLEANUP`         | Flow end       | Remove worktree        |

### Database Schema

```sql
-- Flow state persistence
flow_states (
    id              SERIAL PRIMARY KEY,
    flow_uuid       VARCHAR(255) NOT NULL,
    method_name     VARCHAR(255) NOT NULL,
    timestamp       TIMESTAMPTZ NOT NULL,
    state_json      JSONB NOT NULL
)

-- Async human-in-the-loop
pending_feedback (
    id              SERIAL PRIMARY KEY,
    flow_uuid       VARCHAR(255) UNIQUE NOT NULL,
    context_json    JSONB NOT NULL,
    state_json      JSONB NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL
)

-- Issue tracking
requests (
    id              SERIAL PRIMARY KEY,
    issue_number    INTEGER NOT NULL,
    request_text    TEXT NOT NULL,
    status          VARCHAR(50) NOT NULL,
    commit          VARCHAR(255),
    created_at      TIMESTAMPTZ
)

-- Payment tracking (manual mode)
payments (
    id              SERIAL PRIMARY KEY,
    issue_number    INTEGER NOT NULL,
    payment_id      VARCHAR(255),
    amount          INTEGER,
    currency        VARCHAR(10),
    payment_method  VARCHAR(50),
    status          VARCHAR(50),
    created_at      TIMESTAMPTZ,
    verified_at     TIMESTAMPTZ
)
```

---

## Environment Variables

### Required

| Variable                    | Description                             | Example                                          |
| --------------------------- | --------------------------------------- | ------------------------------------------------ |
| `DATABASE_URL`              | PostgreSQL connection string            | `postgresql://user:pass@localhost:5432/polycode` |
| `REDIS_HOST`                | Redis hostname                          | `localhost`                                      |
| `REDIS_PORT`                | Redis port                              | `6379`                                           |
| `GITHUB_APP_ID`             | GitHub App ID                           | `123456`                                         |
| `GITHUB_APP_PRIVATE_KEY`    | GitHub App private key (with `\n`)      | `-----BEGIN RSA PRIVATE KEY-----\n...`           |
| `GITHUB_APP_WEBHOOK_SECRET` | Webhook secret for signature validation | `your-webhook-secret`                            |

### LLM Configuration

| Variable          | Description                  | Default  |
| ----------------- | ---------------------------- | -------- |
| `OPENAI_API_KEY`  | OpenAI API key               | -        |
| `OPENAI_URL_BASE` | Custom OpenAI-compatible URL | -        |
| `MODEL`           | Default model identifier     | `gpt-4o` |

### Context+ (Optional)

| Variable             | Description             | Default                  |
| -------------------- | ----------------------- | ------------------------ |
| `OLLAMA_HOST`        | Ollama server URL       | `http://localhost:11434` |
| `OLLAMA_EMBED_MODEL` | Embedding model         | `nomic-embed-text`       |
| `OLLAMA_CHAT_MODEL`  | Chat model for Context+ | `gemma2:27b`             |

### Application

| Variable    | Description                  | Default   |
| ----------- | ---------------------------- | --------- |
| `APP_RUN`   | Default run mode             | `api`     |
| `APP_HOST`  | Server host                  | `0.0.0.0` |
| `APP_PORT`  | Server port                  | `5000`    |
| `LOG_LEVEL` | Logging verbosity            | `INFO`    |
| `DATA_PATH` | Worktree storage path        | `/data`   |
| `SSH_KEY`   | SSH private key for git push | -         |

---

## Available Scripts

### Package Management

```bash
uv sync                   # Install all dependencies
uv add <package>          # Add a new dependency
uv add --dev <package>    # Add development dependency
uv lock                   # Update lock file
```

### Linting & Formatting

```bash
uv run ruff check .                    # Check lint errors
uv run ruff check --fix .              # Auto-fix lint errors
uv run ruff format .                   # Format code
uv run pyright                         # Type checking
```

### Database

```bash
uv run polycode db init                # Initialize database tables
uv run polycode db reset               # Reset database (warning: destructive)
```

---

## CLI Commands

```bash
# Show help
uv run polycode --help
uv run polycode <command> --help

# Server management
uv run polycode server webhook --host 0.0.0.0 --port 5000 --reload
uv run polycode server socketio --host 0.0.0.0 --port 5001

# Celery worker
uv run polycode worker start --queues celery,default --loglevel=info
uv run polycode worker flower --port=5555

# Flow execution
uv run polycode flow run ralph --issue 42 --repo owner/repo

# GitHub project management
uv run polycode project list --installation 12345
uv run polycode project status --issue 42

# Database
uv run polycode db init
uv run polycode db status
```

---

## Testing

### Run Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_flows.py

# Run single test
uv run pytest tests/test_flows.py::test_ralph_flow_setup

# Run tests matching pattern
uv run pytest -k "ralph"

# Verbose output
uv run pytest -v

# Stop after first failure
uv run pytest --maxfail=1

# With coverage
uv run pytest --cov=src
```

### Test Structure

```
tests/
├── __init__.py
├── test_flows.py              # Flow tests
├── test_gitcore.py            # Git operations tests
├── test_github_manager.py     # GitHub API tests
├── test_agents_md_loader.py   # AGENTS.md loader tests
├── test_project_manager_plugin.py
└── test_retro.py              # Retrospective tests
```

### Writing Tests

```python
"""Test module docstring."""

from unittest.mock import MagicMock, patch

from project_manager.github import GitHubProjectManager
from project_manager.types import ProjectConfig


def test_has_label_returns_true_when_label_exists():
    """Test that has_label returns True when the label is present."""
    # Arrange
    config = ProjectConfig(
        repo_owner="testowner",
        repo_name="testrepo",
        token="fake_token",
    )
    manager = GitHubProjectManager(config)
    mock_repo = MagicMock()
    mock_pr = MagicMock()
    mock_pr.labels = [MagicMock(name="approved")]
    mock_repo.get_pull.return_value = mock_pr
    manager.github_client.get_repo = MagicMock(return_value=mock_repo)

    # Act
    result = manager.has_label(123, "approved")

    # Assert
    assert result is True
    mock_repo.get_pull.assert_called_once_with(123)
```

---

## Workflows

### Ralph Flow (`ralph`)

Iterative development with automatic verification loops.

**Flow Steps:**

1. **Setup** - Initialize git worktree, load issue context
2. **Plan** - Decompose task into ordered user stories via `PlanCrew`
3. **Implement** - Execute each story via `RalphCrew`:
   - Implement code changes
   - Run tests
   - If tests fail: retry with error context (max 3 attempts)
   - If tests pass: commit and proceed to next story
4. **Verify** - Final build and test verification
5. **Cleanup** - Push changes, create PR, remove worktree

**Tools Available to Ralph Agents:**

| Tool                 | Description                          |
| -------------------- | ------------------------------------ |
| `FileReadTool`       | Read file contents                   |
| `FileWriterTool`     | Write/modify files                   |
| `DirectoryReadTool`  | Explore directory structure          |
| `ExecTool`           | Execute shell commands (build, test) |
| `AgentsMDLoaderTool` | Load AGENTS.md context files         |

**Safety Features:**

- Per-story commits (atomic changes)
- Maximum 3 retry iterations per story
- Error context included in retries
- Automatic worktree cleanup

### Specify Flow (`specify`)

Feature specification and planning workflow for larger features.

---

## GitHub App Integration

### Setup

1. **Create GitHub App**

   Go to <https://github.com/settings/apps/new>

   Configure:

   - **App name**: Your app name
   - **Webhook URL**: Your server URL + `/webhook/github`
   - **Webhook secret**: Generate a secure secret
   - **Permissions**:
     - Issues: Read & Write
     - Pull requests: Read & Write
     - Contents: Read & Write
     - Projects: Read & Write
     - Metadata: Read-only

2. **Generate Private Key**

   After creating the app, generate a private key and add to `.env`:

   ```bash
   GITHUB_APP_PRIVATE_KEY=$(cat private-key.pem | awk '{printf "%s\\n", $0}' | tr -d '\n')
   ```

3. **Install App**

   Install the app on target repositories from the app settings page.

4. **Create Label Mappings**

   ```bash
   curl -X POST http://localhost:5000/mappings \
     -H "Content-Type: application/json" \
     -d '{
       "installation_id": 12345,
       "label_name": "ralph",
       "flow_name": "ralph_flow",
       "priority": 0
     }'
   ```

### Available Endpoints

| Endpoint          | Method | Description               |
| ----------------- | ------ | ------------------------- |
| `/`               | GET    | App info and status       |
| `/health`         | GET    | Health check              |
| `/webhook/github` | POST   | GitHub webhook handler    |
| `/installations`  | GET    | List active installations |
| `/mappings`       | GET    | List label mappings       |
| `/mappings`       | POST   | Create label mapping      |

### Triggering Flows

1. Create an issue in a connected repository
2. Add the mapped label (e.g., `ralph`)
3. Webhook triggers flow execution automatically

---

## Docker Deployment

### Build Image

```bash
make docker_build
# or
docker build -t ghcr.io/xeroc/polycode:latest .
```

### Run Container

```bash
# API server
docker run -p 5000:5000 \
  -e DATABASE_URL=postgresql://... \
  -e REDIS_HOST=redis \
  -e GITHUB_APP_ID=123456 \
  -e GITHUB_APP_PRIVATE_KEY="-----BEGIN..." \
  -e GITHUB_APP_WEBHOOK_SECRET=secret \
  -v /data:/data \
  ghcr.io/xeroc/polycode:latest api

# Celery worker
docker run \
  -e DATABASE_URL=postgresql://... \
  -e REDIS_HOST=redis \
  -e OLLAMA_HOST=http://ollama:11434 \
  -e SSH_KEY="$(cat ~/.ssh/id_rsa)" \
  ghcr.io/xeroc/polycode:latest worker

# Socket.IO server
docker run -p 5001:5000 \
  ghcr.io/xeroc/polycode:latest socketio
```

### Docker Compose

```yaml
services:
  api:
    image: ghcr.io/xeroc/polycode:latest
    command: api
    ports:
      - "5000:5000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/polycode
      - REDIS_HOST=redis
      - GITHUB_APP_ID=${GITHUB_APP_ID}
      - GITHUB_APP_PRIVATE_KEY=${GITHUB_APP_PRIVATE_KEY}
      - GITHUB_APP_WEBHOOK_SECRET=${GITHUB_APP_WEBHOOK_SECRET}
    depends_on:
      - db
      - redis

  worker:
    image: ghcr.io/xeroc/polycode:latest
    command: worker
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/polycode
      - REDIS_HOST=redis
      - OLLAMA_HOST=http://ollama:11434
      - SSH_KEY=${SSH_KEY}
    volumes:
      - data:/data
    depends_on:
      - db
      - redis
      - ollama

  socketio:
    image: ghcr.io/xeroc/polycode:latest
    command: socketio
    ports:
      - "5001:5000"
    environment:
      - REDIS_HOST=redis
    depends_on:
      - redis

  db:
    image: postgres:16
    environment:
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=polycode
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7
    volumes:
      - redisdata:/data

  ollama:
    image: ollama/ollama
    volumes:
      - ollamadata:/root/.ollama

volumes:
  pgdata:
  redisdata:
  ollamadata:
  data:
```

---

## Troubleshooting

### Database Connection Issues

**Error:** `could not connect to server: Connection refused`

**Solution:**

1. Verify PostgreSQL is running: `docker ps` or `pg_isready`
2. Check `DATABASE_URL` format: `postgresql://USER:PASSWORD@HOST:PORT/DATABASE`
3. Ensure database exists: `createdb polycode`

### Redis Connection Issues

**Error:** `Error connecting to Redis`

**Solution:**

1. Verify Redis is running: `redis-cli ping`
2. Check `REDIS_HOST` and `REDIS_PORT` values
3. For Docker: ensure containers are on same network

### Celery Worker Not Processing Tasks

**Error:** Tasks queued but not executing

**Solution:**

```bash
# Check worker is running
uv run polycode worker start --queues celery,default --loglevel=debug

# Check Flower dashboard
uv run polycode worker flower
# Open http://localhost:5555
```

### GitHub App Authentication Failures

**Error:** `JWT authentication failed`

**Solution:**

1. Verify `GITHUB_APP_ID` matches your app
2. Ensure private key has proper newlines:

   ```bash
   echo "$GITHUB_APP_PRIVATE_KEY" | head -1
   # Should show: -----BEGIN RSA PRIVATE KEY-----
   ```

3. Check app is installed on the repository

### LLM API Errors

**Error:** `OpenAI API error`

**Solution:**

1. Verify `OPENAI_API_KEY` is set
2. Check rate limits
3. For custom endpoints, verify `OPENAI_URL_BASE`

### Context+ Not Working

**Error:** `Context+ MCP connection failed`

**Solution:**

1. Ensure Ollama is running: `ollama serve`
2. Pull required models:

   ```bash
   ollama pull nomic-embed-text
   ollama pull gemma2:27b
   ```

3. Verify Context+ is installed: `bun install -g contextplus`
4. Test MCP server: `bunx contextplus skeleton .`

### Git Operations Failing

**Error:** `Permission denied (publickey)`

**Solution:**

1. For Docker: ensure `SSH_KEY` environment variable is set
2. For local: verify SSH key has access to repository
3. Add GitHub to known hosts:

   ```bash
   ssh-keyscan github.com >> ~/.ssh/known_hosts
   ```

### Import Errors

**Error:** `ModuleNotFoundError: No module named 'xxx'`

**Solution:**

```bash
# Ensure virtual environment is active
uv sync

# Run with uv
uv run polycode --help
```

---

## Resources

- [CrewAI Documentation](https://docs.crewai.com/)
- [GitHub Apps Documentation](https://docs.github.com/en/apps)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Celery Documentation](https://docs.celeryq.dev/)

## License

MIT
