# Polycode Source

Multi-agent AI development automation powered by [CrewAI](https://crewai.com).

## Structure

```
src/
├── ralph/                    # Ralph Flow - fast iterative development
│   ├── crews/
│   │   ├── plan_crew/        # Issue decomposition
│   │   └── ralph_crew/       # Implementation with verification loop
│   └── __init__.py           # Ralph flow definition
├── feature_dev/               # Feature Dev Flow - comprehensive feature development
│   ├── crews/
│   │   ├── plan_crew/
│   │   ├── implement_crew/
│   │   ├── verify_crew/
│   │   ├── test_crew/
│   │   └── review_crew/
│   └── __init__.py
├── github_app/                # GitHub App webhook server
│   ├── app.py                # FastAPI application
│   ├── handlers.py            # Webhook event handlers
│   └── ...
├── project_manager/           # Project management abstraction
│   ├── base.py               # Abstract ProjectManager interface
│   ├── github.py             # GitHub Projects V2 implementation
│   ├── flow_runner.py         # Flow execution orchestration
│   ├── flow_state.py         # State persistence
│   ├── webhook.py            # FastAPI webhook server
│   └── cli.py               # CLI commands
├── celery_tasks/             # Async task processing
├── persistence/              # Database layer (PostgreSQL)
├── tools/                   # Custom CrewAI tools
└── flowbase.py              # Base flow classes
```

## Installation

Ensure you have Python >=3.10 <3.14 installed. This project uses [UV](https://docs.astral.sh/uv/) for dependency management.

```bash
# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with OPENAI_API_KEY, GITHUB_TOKEN, DATABASE_URL, etc.
```

## Running Flows Locally

```bash
# Run Ralph Flow (interactive)
uv run ralph

# Run Feature Dev example
uv run example

# Run project manager CLI
python -m project_manager.cli --help
```

## Webhook Development

```bash
# Start webhook server
export GITHUB_TOKEN=ghp_xxx
export REPO_OWNER=xeroc
export REPO_NAME=demo
export PROJECT_IDENTIFIER=1
export GITHUB_WEBHOOK_SECRET=your-secret

uv run uvicorn github_app.app:app --reload --host 0.0.0.0 --port 8000
```

Webhook will be available at `http://localhost:8000/webhook/github`

## Testing

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_ralph.py

# Run tests matching pattern
uv run pytest -k "label"

# Verbose output
uv run pytest -v
```

## Development

```bash
# Linting
uv run ruff check .              # Check for lint errors
uv run ruff check --fix .        # Auto-fix lint errors
uv run ruff format .             # Format code

# Type checking
uv run pyright                 # Type check (via pre-commit)

# Pre-commit hooks
pre-commit run --all-files       # Run all hooks
```

## CrewAI Patterns

This project uses modern CrewAI patterns. See `/home/xeroc/projects/polycode/src/AGENTS.md` for complete reference.

Key patterns used:

- **`@CrewBase` decorator** on crew classes
- **YAML configuration** for agents and tasks
- **Flow orchestration** with `@start`, `@listen`, `@router` decorators
- **Structured state** using Pydantic models
- **Human-in-the-loop** with `@human_feedback` decorator

## Documentation

- [PROJECT.md](../../PROJECT.md) - Project vision and roadmap
- [README.md](../../README.md) - Main project README
- [project_manager/README.md](./project_manager/README.md) - Project manager docs
- [src/AGENTS.md](./AGENTS.md) - CrewAI reference guide

## License

MIT
