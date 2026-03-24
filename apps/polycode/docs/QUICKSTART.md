# Quick Start Guide

## Installation

```bash
cd apps/polycode
uv sync
```

## Configuration

Create `.env` file with your LLM API key:

```bash
cp .env.example .env
# Edit .env and add your API key
```

Required environment variables:

```bash
# LLM Configuration
OPENAI_API_KEY=sk-...

# Database
DATABASE_URL=postgresql://user:password@localhost/polycode

# Redis (for Celery)
REDIS_HOST=localhost
REDIS_PORT=6379

# GitHub
GITHUB_TOKEN=ghp_...
REPO_OWNER=xeroc
REPO_NAME=demo
PROJECT_IDENTIFIER=1
```

## CLI Overview

Polycode uses a Typer-based CLI with subcommands:

```bash
# Main entry point
polycode --help

# Available subcommands
polycode server --help      # Server management
polycode worker --help      # Celery worker management
polycode flow --help        # Flow execution
polycode project --help     # GitHub project management
polycode db --help          # Database operations
```

## Usage Examples

### 1. Start the webhook server

```bash
# Start the FastAPI webhook server
polycode server start

# With custom host/port
polycode server start --host 0.0.0.0 --port 8080
```

### 2. Start Celery workers

```bash
# Start Celery worker for feature development
polycode worker start --queue feature_dev

# Start all workers
polycode worker start

# With specific concurrency
polycode worker start --queue feature_dev --concurrency 4
```

### 3. Run a flow manually

```bash
# List available flows
polycode flow list

# Run Ralph flow (feature development)
polycode flow run ralph --issue 42

# Run with verbose output
polycode flow run ralph --issue 42 --verbose
```

### 4. Project management

```bash
# Sync GitHub issues to project
polycode project sync

# List project items
polycode project list

# Check flow status
polycode project status
```

## Project Structure

```
apps/polycode/
├── src/
│   ├── cli/                    # Typer-based CLI
│   │   ├── main.py             # Main entry point
│   │   ├── project.py          # Project management commands
│   │   ├── flow.py            # Flow execution commands
│   │   ├── server.py           # Webhook server commands
│   │   ├── worker.py           # Celery worker commands
│   │   └── db.py              # Database commands
│   ├── flows/                   # Flow definitions
│   │   ├── base.py             # Base flow classes
│   │   ├── protocol.py          # FlowDef protocol
│   │   ├── registry.py          # FlowRegistry
│   │   └── ralph/              # Ralph flow implementation
│   │       ├── flow.py         # RalphLoopFlow
│   │       ├── module.py       # RalphModule
│   │       └── types.py        # Ralph types
│   ├── crews/                   # CrewAI crews
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
│   │   └── webhook_handler.py  # Webhook processing
│   ├── celery_tasks/            # Celery tasks
│   │   ├── flow_orchestration.py
│   │   ├── agent_execution.py
│   │   ├── webhook_tasks.py
│   │   └── utility_tasks.py
│   ├── gitcore/                # Git operations
│   │   └── hooks.py
│   ├── retro/                  # Retrospectives module
│   │   ├── persistence.py
│   │   └── hooks.py
│   └── bootstrap.py             # Plugin initialization
├── pyproject.toml
├── README.md
└── .env
```

## Architecture Overview

- **CLI**: Typer-based command-line interface with subcommands
- **Flows**: Label-driven workflow orchestration using CrewAI
- **Crews**: AI agent teams for planning, implementing, reviewing code
- **Plugins**: Extensible module system with hooks and models
- **Celery**: Background task processing for long-running flows
- **GitHub App**: Webhook-driven integration with GitHub

## Next Steps

1. **Configure LLM**: Add your API key to `.env`
2. **Test webhook**: Start server and trigger a test issue
3. **Explore flows**: Run `polycode flow list` to see available workflows
4. **Create custom flow**: Extend the flow system with new workflows
5. **Write a plugin**: Add custom hooks and models to extend functionality

## Documentation

- Full README: `README.md`
- CrewAI Docs: <https://docs.crewai.com/>
- CLI: Run `polycode --help` for available commands
