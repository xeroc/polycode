<div align="center">

<h1>Self-hosted AI GitHub bot for automated software development</h1>

<p>Label an issue, and watch your bot plan, implement, and open a PR.<br>
<strong>Polycode brings AI automation to your repos — no black box, no SaaS, your infra.</strong></p>

<br>

[![Python](https://img.shields.io/badge/Python-3.13-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![CrewAI](https://img.shields.io/badge/CrewAI-Multi_Agent-FF6B6B?style=for-the-badge)](https://docs.crewai.com)
[![GitHub App](https://img.shields.io/badge/GitHub-App_Integration-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/apps/polycode-agent/)

[![License](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/xeroc/polycode?style=flat-square)](https://github.com/xeroc/polycode)
[![Python package](https://img.shields.io/badge/pypi-v0.1.0-blue?style=flat-square&logo=pypi)](https://pypi.org/project/polycode/)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=flat-square&logo=docker&logoColor=white)](https://hub.docker.com/r/xeroc/polycode)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-4169E1?style=flat-square&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7+-DC382D?style=flat-square&logo=redis&logoColor=white)](https://redis.io)

</div>

---

## Key Features

- **Multi-agent workflows** with CrewAI framework
- **GitHub App integration** for multi-repo automation
- **Webhook-driven automation** triggered by labels
- **Push to external repos** via GitHub App tokens
- **Label-to-flow mapping** (e.g., `ralph` → `ralph_flow`)
- **Fast iterative workflows** with automated verification

---

## Table of Contents

- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [Architecture](#architecture)
- [Environment Variables](#environment-variables)
- [Available Scripts](#available-scripts)
- [Testing](#testing)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)

---

## Tech Stack

### Polycode (Backend)

| Component           | Technology            |
| ------------------- | --------------------- |
| **Language**        | Python 3.13           |
| **Framework**       | FastAPI               |
| **Multi-Agent**     | CrewAI                |
| **Background Jobs** | Celery                |
| **Message Broker**  | Redis                 |
| **Database**        | PostgreSQL            |
| **ORM**             | SQLAlchemy / SQLModel |
| **Validation**      | Pydantic              |
| **Package Manager** | uv                    |

### Landing (Frontend)

| Component           | Technology       |
| ------------------- | ---------------- |
| **Language**        | TypeScript 5.9   |
| **Framework**       | React 19         |
| **Build Tool**      | Vite 8           |
| **Styling**         | Tailwind CSS 3.4 |
| **Animation**       | Framer Motion    |
| **Icons**           | Lucide React     |
| **Package Manager** | pnpm             |

---

## Project Structure

```
polycode/
├── apps/
│   ├── polycode/                 # Python backend application
│   │   ├── src/
│   │   │   ├── crews/            # CrewAI crew definitions
│   │   │   │   ├── plan_crew/    # Planning crew
│   │   │   │   ├── ralph_crew/   # Ralph implementation crew
│   │   │   │   ├── implement_crew/
│   │   │   │   ├── review_crew/
│   │   │   │   ├── test_crew/
│   │   │   │   ├── verify_crew/
│   │   │   │   └── conversation_crew/
│   │   │   ├── ralph/            # Ralph Loop workflow
│   │   │   ├── feature_dev/      # Feature development workflow
│   │   │   ├── github_app/       # GitHub App webhook server
│   │   │   ├── project_manager/  # Project management utilities
│   │   │   ├── celery_tasks/     # Async task processing
│   │   │   ├── persistence/      # Database layer (PostgreSQL)
│   │   │   ├── channels/         # Real-time communication (SocketIO)
│   │   │   ├── tools/            # Custom CrewAI tools
│   │   │   └── flowbase.py       # Base flow classes
│   │   ├── tests/                # Test files
│   │   ├── task_templates/       # Task template files
│   │   ├── pyproject.toml        # Python project configuration
│   │   ├── uv.lock               # Dependency lock file
│   │   ├── Dockerfile            # Docker build file
│   │   ├── entrypooint.sh        # Container entrypoint
│   │   └── Makefile              # Build commands
│   │
│   └── landing/                  # React frontend (marketing page)
│       ├── src/
│       │   ├── components/       # Reusable UI components
│       │   │   ├── Header.tsx
│       │   │   ├── Footer.tsx
│       │   │   └── ThemeToggle.tsx
│       │   ├── pages/            # Page components
│       │   │   └── Home.tsx
│       │   ├── lib/              # Utilities
│       │   ├── assets/           # Static assets
│       │   ├── App.tsx           # Root component
│       │   ├── main.tsx          # Entry point
│       │   └── index.css         # Global styles
│       ├── public/               # Static files
│       ├── dist/                 # Build output
│       ├── package.json          # NPM dependencies
│       ├── pnpm-lock.yaml        # Dependency lock
│       ├── vite.config.ts        # Vite configuration
│       ├── tailwind.config.js    # Tailwind configuration
│       ├── tsconfig.json         # TypeScript configuration
│       └── index.html            # HTML template
│
├── .github/
│   └── workflows/
│       └── landingpage.yaml      # GitHub Actions deployment
│
├── .pre-commit-config.yaml       # Pre-commit hooks
└── .gitignore
```

---

## Prerequisites

### For Polycode (Backend)

- **Python 3.13** or higher
- **uv** package manager ([install guide](https://docs.astral.sh/uv/))
- **PostgreSQL 15+** (or Docker)
- **Redis 7+** (or Docker)
- **GitHub App** credentials (for webhook integration)

### For Landing (Frontend)

- **Node.js 22** or higher
- **pnpm** package manager

---

## Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/xeroc/polycode.git
cd polycode
```

### 2. Backend Setup (Polycode)

#### Install Dependencies

```bash
cd apps/polycode
uv sync
```

#### Environment Configuration

Copy the example environment file:

```bash
cp .env.example .env
```

Configure the following variables (see [Environment Variables](#environment-variables) for details):

```bash
# Required
GITHUB_APP_ID=12345
GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n..."
DATABASE_URL=postgresql://user:password@localhost:5432/polycode
REDIS_HOST=localhost
REDIS_PORT=6379
OPENAI_API_KEY=sk-your_key_here

# Optional
OLLAMA_HOST=http://localhost:11434
```

#### Start PostgreSQL (Docker)

```bash
docker run --name postgres \
  -e POSTGRES_USER=polycode \
  -e POSTGRES_PASSWORD=polycode \
  -e POSTGRES_DB=polycode \
  -p 5432:5432 \
  -d postgres:16
```

#### Start Redis (Docker)

```bash
docker run --name redis \
  -p 6379:6379 \
  -d redis:7-alpine
```

#### Run Database Migrations

The application uses SQLAlchemy with auto-table creation. On first run:

```bash
uv run python -c "from persistence.postgres import Base, engine; Base.metadata.create_all(engine)"
```

#### Start the API Server

```bash
uv run webhook-server webhook --host 0.0.0.0 --port 8000
```

Or use the entrypoint:

```bash
APP_RUN=api uv run python -m entrypoint
```

#### Start the Celery Worker (Background Jobs)

```bash
uv run celery -A celery_tasks.worker.app worker -Ofair --queues celery,default --loglevel=info
```

#### Start Flower (Celery Monitoring)

```bash
uv run celery -A celery_tasks.worker.app flower --address=0.0.0.0 --port=5555
```

### 3. Frontend Setup (Landing)

#### Install Dependencies

```bash
cd apps/landing
pnpm install
```

#### Environment Configuration

Create `.env` file:

```bash
VITE_N8N_WEBHOOK_URL=https://your-webhook-url.com/webhook/xxx
```

#### Start Development Server

```bash
pnpm dev
```

Open [http://localhost:5173](http://localhost:5173) in your browser.

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        GitHub Webhooks                           │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FastAPI Server                               │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  GitHub App     │  │  Label Mapper   │  │  Webhook Router │  │
│  │  Integration    │  │                 │  │                 │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Celery Task Queue                            │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  Ralph Flow     │  │  Feature Flow   │  │  Custom Flows   │  │
│  │  Tasks          │  │  Tasks          │  │  Tasks          │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     CrewAI Agents                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │  Plan Crew      │  │  Implement Crew │  │  Review Crew    │  │
│  │  (Planning)     │  │  (Coding)       │  │  (QA)           │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│  ┌─────────────────┐  ┌─────────────────┐                       │
│  │  Test Crew      │  │  Verify Crew    │                       │
│  │  (Testing)      │  │  (Validation)   │                       │
│  └─────────────────┘  └─────────────────┘                       │
└─────────────────────────────────────────────────────────────────┘
                                │
              ┌─────────────────┼─────────────────┐
              ▼                 ▼                 ▼
      ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
      │  PostgreSQL  │  │    Redis     │  │   GitHub     │
      │  (State)     │  │  (Queue)     │  │  (Repos)     │
      └──────────────┘  └──────────────┘  └──────────────┘
```

### Request Lifecycle

1. GitHub webhook triggers on issue/PR event
2. FastAPI receives webhook, validates signature
3. Label mapper determines which flow to trigger
4. Task dispatched to Celery queue
5. Celery worker picks up task
6. CrewAI agents execute the workflow
7. Results pushed back to GitHub (PR, comments, commits)
8. State persisted to PostgreSQL

### Ralph Flow

The Ralph Flow is an iterative development workflow with built-in verification:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐
│   Setup     │────▶│    Plan     │────▶│  Ralph Loop     │
│ (Worktree)  │     │  (Stories)  │     │  (Iterative)    │
└─────────────┘     └─────────────┘     └─────────────────┘
                                                │
                    ┌───────────────────────────┤
                    │                           │
                    ▼                           ▼
            ┌─────────────┐             ┌─────────────┐
            │   Verify    │◀────────────│   Commit    │
            │   Build     │             │   Story     │
            └─────────────┘             └─────────────┘
                    │
                    ▼
            ┌─────────────┐
            │    Push     │
            │   & PR      │
            └─────────────┘
```

#### Ralph Loop Control Flow

- **`retry`** → Continue loop with error context (max 3 iterations per story)
- **`story_done`** → Commit current story, proceed to next
- **`done`** → All stories complete, run final verification

### Database Schema

```sql
-- Flow requests tracking
requests
├── id (serial, PK)
├── issue_number (int, not null)
├── request_text (text, not null)
├── status (varchar, not null)
├── commit (varchar, nullable)
└── created_at (timestamp)

-- Payment tracking
payments
├── id (serial, PK)
├── issue_number (int)
├── payment_id (varchar)
├── amount (int)
├── currency (varchar)
├── payment_method (varchar)
├── status (varchar)
├── created_at (timestamp)
└── verified_at (timestamp, nullable)
```

---

## Environment Variables

### Polycode Backend

#### Required

| Variable                 | Description                  | Example                                          |
| ------------------------ | ---------------------------- | ------------------------------------------------ |
| `GITHUB_APP_ID`          | GitHub App ID                | `12345`                                          |
| `GITHUB_APP_PRIVATE_KEY` | GitHub App private key (PEM) | `-----BEGIN RSA PRIVATE KEY-----\n...`           |
| `DATABASE_URL`           | PostgreSQL connection string | `postgresql://user:pass@localhost:5432/polycode` |
| `REDIS_HOST`             | Redis hostname               | `localhost`                                      |
| `REDIS_PORT`             | Redis port                   | `6379`                                           |
| `OPENAI_API_KEY`         | OpenAI API key for LLM calls | `sk-xxx`                                         |

#### Optional

| Variable              | Description                                    | Default                  |
| --------------------- | ---------------------------------------------- | ------------------------ |
| `OLLAMA_HOST`         | Ollama server URL                              | `http://localhost:11434` |
| `APP_RUN`             | Container run mode (`api`, `worker`, `flower`) | `api`                    |
| `APP_HOST`            | Server bind host                               | `0.0.0.0`                |
| `APP_PORT`            | Server port                                    | `5000`                   |
| `LOG_LEVEL`           | Logging verbosity                              | `critical`               |
| `FORWARDED_ALLOW_IPS` | Trusted proxy IPs                              | `*`                      |
| `SSH_KEY`             | SSH private key for git operations             | -                        |

### Landing Frontend

| Variable               | Description                     | Required |
| ---------------------- | ------------------------------- | -------- |
| `VITE_N8N_WEBHOOK_URL` | N8N webhook for waitlist signup | Yes      |

---

## Available Scripts

### Polycode (Backend)

| Command                            | Description                  |
| ---------------------------------- | ---------------------------- |
| `uv sync`                          | Install dependencies         |
| `uv add <package>`                 | Add new dependency           |
| `uv lock`                          | Update lock file             |
| `uv run ruff check .`              | Lint code                    |
| `uv run ruff check --fix .`        | Auto-fix lint errors         |
| `uv run ruff format .`             | Format code                  |
| `uv run pyright`                   | Type check                   |
| `uv run pytest`                    | Run all tests                |
| `uv run pytest tests/test_file.py` | Run specific test file       |
| `uv run pytest -k "pattern"`       | Run tests matching pattern   |
| `uv run webhook-server webhook`    | Start FastAPI webhook server |
| `uv run ralph`                     | Run Ralph flow example       |

### Celery Commands

```bash
# Start worker
uv run celery -A celery_tasks.worker.app worker \
  --queues celery,default \
  --loglevel=info

# Start Flower monitoring
uv run celery -A celery_tasks.worker.app flower \
  --address=0.0.0.0 \
  --port=5555
```

### Landing (Frontend)

| Command        | Description                              |
| -------------- | ---------------------------------------- |
| `pnpm dev`     | Start development server                 |
| `pnpm build`   | Build for production (TypeScript + Vite) |
| `pnpm preview` | Preview production build                 |
| `pnpm lint`    | Run ESLint                               |

### Docker Commands

```bash
# Build Docker image
make docker_build

# Push to registry
make docker_push

# Build and push (combined)
make docker
```

---

## Testing

### Backend Tests

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/test_github_manager.py

# Run specific test function
uv run pytest tests/test_github_manager.py::test_has_label_returns_true_when_label_exists

# Run tests matching pattern
uv run pytest -k "label"
```

### Test Structure

```
tests/
├── test_github_manager.py    # GitHub API tests
├── test_project_manager.py   # Project management tests
└── ...
```

### Writing Tests

```python
"""Test module docstring."""

from unittest.mock import MagicMock
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
```

---

## Deployment

### Landing Page (GitHub Pages)

The landing page is automatically deployed to GitHub Pages via GitHub Actions.

**Trigger:** Push to `main` branch

**URL:** [https://polycod.ing](https://polycod.ing)

**Manual deploy:**

```bash
gh workflow run landingpage.yaml
```

### Polycode Backend (Docker)

#### Build and Push

```bash
cd apps/polycode

# Build with timestamp version
make docker

# Or manually:
docker build -t ghcr.io/xeroc/polycode:$(date +%Y%m%d%H%M) .
docker push ghcr.io/xeroc/polycode:$(date +%Y%m%d%H%M)
```

#### Run Container

```bash
# Run API server
docker run -p 5000:5000 \
  -e DATABASE_URL=postgresql://... \
  -e REDIS_HOST=redis \
  -e GITHUB_APP_ID=12345 \
  -e GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----..." \
  -e OPENAI_API_KEY=sk-... \
  ghcr.io/xeroc/polycode:latest api

# Run Celery worker
docker run \
  -e DATABASE_URL=postgresql://... \
  -e REDIS_HOST=redis \
  -e GITHUB_APP_ID=12345 \
  -e GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----..." \
  -e SSH_KEY="$(cat ~/.ssh/id_rsa)" \
  ghcr.io/xeroc/polycode:latest worker

# Run Flower monitoring
docker run -p 5555:5555 \
  -e REDIS_HOST=redis \
  ghcr.io/xeroc/polycode:latest flower
```

#### Docker Compose Example

```yaml
version: "3.8"

services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_USER: polycode
      POSTGRES_PASSWORD: polycode
      POSTGRES_DB: polycode
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  api:
    image: ghcr.io/xeroc/polycode:latest
    command: api
    ports:
      - "5000:5000"
    environment:
      DATABASE_URL: postgresql://polycode:polycode@postgres:5432/polycode
      REDIS_HOST: redis
      GITHUB_APP_ID: ${GITHUB_APP_ID}
      GITHUB_APP_PRIVATE_KEY: ${GITHUB_APP_PRIVATE_KEY}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    depends_on:
      - postgres
      - redis

  worker:
    image: ghcr.io/xeroc/polycode:latest
    command: worker
    environment:
      DATABASE_URL: postgresql://polycode:polycode@postgres:5432/polycode
      REDIS_HOST: redis
      GITHUB_APP_ID: ${GITHUB_APP_ID}
      GITHUB_APP_PRIVATE_KEY: ${GITHUB_APP_PRIVATE_KEY}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      SSH_KEY: ${SSH_KEY}
    depends_on:
      - postgres
      - redis

volumes:
  postgres_data:
  redis_data:
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

**Error:** `ConnectionError: Error connecting to Redis`

**Solution:**

1. Verify Redis is running: `docker ps` or `redis-cli ping`
2. Check `REDIS_HOST` and `REDIS_PORT` values
3. If using Docker, ensure containers share a network

### Celery Worker Not Processing Tasks

**Symptoms:** Tasks queued but never executed

**Solution:**

1. Verify worker is running: `celery -A celery_tasks.worker.app inspect active`
2. Check queue names match: `--queues celery,default`
3. Review worker logs for errors

### GitHub App Authentication Issues

**Error:** `Bad credentials` or `401 Unauthorized`

**Solution:**

1. Verify `GITHUB_APP_ID` and `GITHUB_APP_PRIVATE_KEY` are correctly set
2. Ensure the private key is properly formatted (including newlines)
3. For GitHub Apps, ensure app is installed on target repository

### Import Errors (Module Not Found)

**Error:** `ModuleNotFoundError: No module named 'xxx'`

**Solution:**

```bash
# Sync dependencies
uv sync

# If using Docker, rebuild image
docker build --no-cache -t ghcr.io/xeroc/polycode:latest .
```

### Landing Page Build Issues

**Error:** `VITE_N8N_WEBHOOK_URL is not defined`

**Solution:**

1. Create `.env` file in `apps/landing/`
2. Add required environment variables
3. Rebuild: `pnpm build`

### Pre-commit Hook Failures

**Error:** `pyright` or `ruff` failures

**Solution:**

```bash
# Auto-fix lint issues
uv run ruff check --fix .
uv run ruff format .

# Run type check
uv run pyright

# Run all pre-commit hooks
pre-commit run --all-files
```

---

## GitHub App Integration

### Setup GitHub App

1. **Create GitHub App** at [https://github.com/settings/apps/new](https://github.com/settings/apps/new)

2. **Configure permissions:**
   - Issues: Read & Write
   - Projects: Read & Write
   - Contents: Read & Write
   - Pull requests: Read & Write
   - Metadata: Read (required)

3. **Set webhook URL:** `https://your-domain.com/webhook`

4. **Generate private key** and save to `.env`:

   ```
   GITHUB_APP_ID=12345
   GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n..."
   ```

5. **Install app** on target repositories

### Label-to-Flow Mapping

Configure which labels trigger which flows:

```bash
curl -X POST http://localhost:8000/mappings \
  -H "Content-Type: application/json" \
  -d '{
    "installation_id": 12345,
    "label_name": "ralph",
    "flow_name": "ralph_flow"
  }'
```

---

## Code Style

### Python (Backend)

- Line length: 120 characters
- Enabled rules: E, F, I, N, W (E501 ignored)
- Use modern Python 3.10+ type annotations (`list[str]` over `List[str]`)
- Run `uv run ruff check --fix .` before committing

### TypeScript (Frontend)

- ESLint with React Hooks and React Refresh plugins
- Strict TypeScript configuration
- Run `pnpm lint` before committing

---

## Pre-commit Hooks

Configured hooks (`.pre-commit-config.yaml`):

- **trailing-whitespace**: Remove trailing whitespace
- **commitizen**: Conventional commits with gitmoji
- **markdownlint**: Markdown linting
- **autoflake**: Remove unused imports and variables
- **pyright**: Python type checking

Run manually:

```bash
pre-commit run --all-files
```

---

## Resources

- [CrewAI Documentation](https://docs.crewai.com/)
- [GitHub Apps Documentation](https://docs.github.com/en/apps)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Celery Documentation](https://docs.celeryq.dev/)
- [Vite Documentation](https://vite.dev/)

---

## License

MIT
