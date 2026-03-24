# Polycode CLI Usage

## Installation

```bash
cd apps/polycode
uv sync
```

## CLI Overview

Polycode uses **Typer** as the CLI framework with subcommands organized by functionality.

### Main Command

```bash
# Show help for all commands
polycode --help

# Enable verbose (DEBUG) logging
polycode --verbose
polycode -v
```

## Subcommands

### `polycode server` - Webhook Server

Manage the FastAPI webhook server for GitHub integration.

```bash
# Start webhook server
polycode server start

# Start with custom settings
polycode server start --host 0.0.0.0 --port 8080

# Show health check
polycode server health
```

### `polycode worker` - Celery Workers

Manage Celery workers for background task processing.

```bash
# Start all workers
polycode worker start

# Start specific queue
polycode worker start --queue feature_dev

# Start with custom concurrency
polycode worker start --concurrency 4

# Start monitoring only
polycode worker start --queue monitoring

# Start webhook workers
polycode worker start --queue webhooks
```

### `polycode flow` - Flow Execution

Execute and manage CrewAI flows.

```bash
# List available flows
polycode flow list

# Run a flow (e.g., Ralph for feature development)
polycode flow run ralph --issue 42

# Run with verbose output
polycode flow run ralph --issue 42 --verbose

# Show flow status
polycode flow status --flow-id <id>
```

### `polycode project` - Project Management

Manage GitHub projects and issues.

```bash
# Sync all open issues to project
polycode project sync

# Sync with verbose output
polycode project sync --verbose

# List all project items
polycode project list

# Check flow status for current project
polycode project status
```

### `polycode db` - Database Management

Manage PostgreSQL database operations.

```bash
# Show database status
polycode db status

# Reset database (development only!)
polycode db reset

# Create tables
polycode db create-tables

# Run migrations
polycode db migrate
```

## Environment Configuration

Create a `.env` file with required variables:

```bash
# Required: LLM
OPENAI_API_KEY=sk-...

# Required: Database
DATABASE_URL=postgresql://user:password@localhost/polycode

# Required: Redis (Celery)
REDIS_HOST=localhost
REDIS_PORT=6379

# Required: GitHub
GITHUB_TOKEN=ghp_xxx
REPO_OWNER=xeroc
REPO_NAME=demo
PROJECT_IDENTIFIER=1

# Optional: Status mappings
STATUS_TODO="Todo"
STATUS_READY="Ready"
STATUS_IN_PROGRESS="In progress"
STATUS_REVIEWING="Reviewing"
STATUS_DONE="Done"
STATUS_BLOCKED="Blocked"

# Optional: Webhook secret
GITHUB_WEBHOOK_SECRET=your-secret
```

## Quick Start

### 1. Webhook Mode (Recommended)

```bash
# Terminal 1: Start webhook server
polycode server start

# Terminal 2: Start Celery workers
polycode worker start

# Terminal 3: Check status
polycode project status

# Trigger a flow via GitHub webhook or manually
polycode flow run ralph --issue 42
```

### 2. Development Mode

```bash
# Run flow directly
polycode flow run ralph --issue 42 --verbose

# Sync issues
polycode project sync

# List project items
polycode project list
```

## Webhook Setup

### GitHub Configuration

1. Go to repository Settings → Webhooks
2. Add webhook:
   - **Payload URL**: `http://your-server:8000/webhook/github`
   - **Content type**: `application/json`
   - **Secret**: Match `GITHUB_WEBHOOK_SECRET`
   - **Events**: Select "Issues"
3. Save webhook

### Endpoints

| Endpoint           | Method | Description                       |
| ------------------ | ------ | --------------------------------- |
| `/webhook/github`  | POST   | GitHub webhook handler            |
| `/health`          | GET    | Health check + active flow status |
| `/flows/{flow_id}` | GET    | Get flow execution status         |

### Testing Webhook

```bash
# Health check
curl http://localhost:8000/health

# Manual flow trigger
polycode flow run ralph --issue 42
```

## Examples

### List Available Flows

```bash
$ polycode flow list

📋 Available flows:
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Name         ┃ Description                   ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━┩
┃ ralph         ┃ Feature development orchestrator  ┃
┗━━━━━━━━━━━━┻━━━━━━━━━━━━━━━━━━━━━━━━┛
Found 1 flow(s)
```

### Run Flow with Issue

```bash
# Trigger Ralph flow for issue #42
polycode flow run ralph --issue 42

# Output:
🚀 Starting flow: ralph
📋 Processing issue: #42 - Add authentication feature
⚙️ Flow ID: flow-abc123...
```

### Sync Issues to Project

```bash
# Sync all open issues
polycode project sync

# Output:
🔄 Syncing issues to project...
Added 3 issues to project
```

### List Project Items

```bash
# Show all project items with status
polycode project list

# Output:
#  42 [In progress ] Add new authentication feature
#  43 [Ready       ] Fix bug in login flow
#  44 [Ready       ] Update API documentation
#  45 [Ready       ] Refactor database queries
#  46 [Todo        ] Add unit tests
#  47 [Done        ] Setup CI/CD pipeline
```

## Development

### Run Commands Directly

```bash
# Without installation, run as module
python -m cli.main --help

# Or use uv run
uv run python -m cli.main --help
```

### Testing

```bash
# Type check
uv run pyright

# Lint
uv run ruff check --fix .

# Format
uv run ruff format .

# Run tests
uv run pytest
```

## Architecture

```
┌─────────────────────────────────────────────┐
│         GitHub Projects (SOT)            │
│  ┌───────────────────────────────────┐    │
│  │ Status: Todo → Ready            │    │
│  │         → In Progress           │    │
│  │         → Reviewing → Done       │    │
│  └───────────────────────────────────┘    │
└─────────────────────────────────────────────┘
                  ↓
┌─────────────────────────────────────────────┐
│         Polycode CLI (Typer)          │
├─────────────────────────────────────────────┤
│ Commands:                             │
│  - server   (webhook management)       │
│  - worker   (Celery workers)          │
│  - flow     (execution)                │
│  - project  (GitHub integration)        │
│  - db       (database)                │
└─────────────────────────────────────────────┘
```

## Dependencies

| Package      | Purpose                        |
| ------------ | ------------------------------ |
| `typer`      | CLI framework with subcommands |
| `fastapi`    | Webhook server                 |
| `uvicorn`    | ASGI server for FastAPI        |
| `crewai`     | Flow and crew orchestration    |
| `celery`     | Background task processing     |
| `redis`      | Celery broker                  |
| `pygithub`   | GitHub API client              |
| `sqlalchemy` | PostgreSQL persistence         |
| `pydantic`   | Data validation                |
| `rich`       | Terminal formatting            |
