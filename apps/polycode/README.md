# Polycode 🚀

Multi-agent software development automation using CrewAI with GitHub App integration for webhook-driven workflows.

## Overview

Polycode automates software development tasks using AI-powered multi-agent workflows built with CrewAI. It integrates as a GitHub App to provide seamless automation across multiple repositories.

**Key Features:**

- **Multi-agent workflows** with CrewAI framework
- **GitHub App integration** for multi-repo automation
- **Webhook-driven automation** triggered by labels
- **Push to external repos** via GitHub App tokens
- **Label-to-flow mapping** (e.g., `ralph` → `ralph_flow`)

### Available Workflows

- **Ralph Flow** (`ralph`): Fast iterative implementation with automated verification
- **Feature Development Flow** (`feature-dev`): Comprehensive feature implementation with planning, testing, and review

## Ralph Flow

The Ralph Flow is an iterative development workflow that implements changes with built-in verification loops. It's designed for fast, reliable code changes with automatic quality checks.

### How It Works

1. **Setup** - Initialize worktree and pick up the issue
2. **Plan** - Decompose the task into ordered user stories
3. **Ralph Loop** - Iterative implementation with verification:
   - Implement the current story
   - Run tests to verify changes
   - If tests fail, retry with error context (max 3 iterations)
   - If tests pass, commit the story and move to next
4. **Verify Build** - Final build and test verification
5. **Push & PR** - Push changes and create pull request

### Ralph Loop Control Flow

The loop uses a router-based mechanism with status outputs:

- **`retry`** → Continue loop with error context included
- **`story_done`** → Commit current story, proceed to next
- **`done`** → All stories complete, run final verification

Key safety features:

- **Per-Story Commits**: Each story is committed immediately upon completion
- **Safety Brake**: Maximum 3 iterations per story prevents runaway processes
- **Error Context**: Agent receives previous errors for smarter retries

### Tools Available to Ralph Agents

- **FileReadTool** - Read file contents
- **FileWriterTool** - Write/modify files
- **DirectoryReadTool** - Explore directory structure
- **ExecTool** - Execute shell commands (build, test, lint)
- **AgentsMDLoaderTool** - Load AGENTS.md context files

## Feature Development Flow

A comprehensive workflow for larger feature implementations:

1. **Plan** - Decompose task into ordered user stories
2. **Implement** - Implement each story with tests
3. **Push** - Push changes to repository
4. **Create PR** - Create pull request
5. **Review** - Code review with feedback

## Project Structure

```
polycode/
├── src/
│   ├── ralph/               # Ralph Loop workflow
│   │   ├── crews/
│   │   │   ├── plan_crew/   # Planning crew
│   │   │   └── ralph_crew/  # Implementation crew
│   │   └── __init__.py      # Ralph flow definition
│   ├── feature_dev/         # Feature development workflow
│   │   └── crews/
│   │       ├── plan_crew/
│   │       ├── implement_crew/
│   │       ├── verify_crew/
│   │       ├── test_crew/
│   │       └── review_crew/
│   ├── github_app/          # GitHub App integration
│   ├── project_manager/     # Project management utilities
│   ├── celery_tasks/        # Async task processing
│   ├── persistence/         # Database layer
│   ├── tools/               # Custom CrewAI tools
│   └── flowbase.py          # Base flow classes
├── tests/                   # Test files
└── pyproject.toml           # Project configuration
```

## Installation

### Prerequisites

- Python 3.13 or higher
- `uv` package manager

### Setup

```bash
# Install dependencies
uv sync

# Configure environment
cp .env.example .env
# Edit .env with your credentials
```

Required environment variables:

- `GITHUB_TOKEN` - GitHub personal access token
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_HOST` / `REDIS_PORT` - Redis configuration
- `OPENAI_API_KEY` - OpenAI API key

### Context+ Integration (Optional)

Context+ provides semantic code intelligence via MCP. Enable by passing `project_root` to the implement crew:

```bash
# Required for Context+ (local Ollama)
OLLAMA_HOST=http://localhost:11434
OLLAMA_EMBED_MODEL=nomic-embed-text
OLLAMA_CHAT_MODEL=gemma2:27b
```

Setup:

```bash
# Install Ollama and models
ollama serve
ollama pull nomic-embed-text
ollama pull gemma2:27b

# Install Context+
bun install -g contextplus

# Test MCP server
bunx contextplus skeleton .
```

## Usage

### Running Flows

```bash
# Run Ralph flow example
uv run ralph

# Run feature development example
uv run example
```

### GitHub App Integration

Polycode includes GitHub App support for webhook-driven automation:

1. **Create GitHub App** at <https://github.com/settings/apps/new>
2. **Configure permissions**: Issues, Projects, Contents, Pull requests (Read & Write)
3. **Set webhook URL** and secret
4. **Generate private key** and add to `.env`
5. **Install app** on target repositories
6. **Create label mappings** to trigger flows

### Label-to-Flow Mapping

```bash
# Map "ralph" label to ralph flow
curl -X POST http://localhost:8000/mappings \
  -H "Content-Type: application/json" \
  -d '{
    "installation_id": 12345,
    "label_name": "ralph",
    "flow_name": "ralph_flow"
  }'
```

## Development

### Commands

```bash
uv sync                   # Install dependencies
uv run ruff check .       # Lint
uv run ruff format .      # Format
uv run pytest             # Run tests
uv run pyright            # Type check
```

### Code Style

- Line length: 79 characters
- Use modern Python 3.10+ type annotations
- See `src/AGENTS.md` for complete guidelines

## Resources

- [CrewAI Documentation](https://docs.crewai.com/)
- [GitHub Apps Docs](https://docs.github.com/en/apps)

## License

MIT [LICENSE](./LICENSE)
