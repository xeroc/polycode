# Polycode 🚀

Polycode workflows implemented with CrewAI - Multi-agent software development automation.

## Overview

This project implements the polycode workflow system using CrewAI framework. Each polycode workflow is represented as a separate "Crew" with specialized AI agents that collaborate to complete complex software development tasks.

**Key Features:**

- **Multi-agent workflows** with CrewAI framework
- **GitHub App integration** for multi-repo automation
- **Webhook-driven automation** triggered by labels
- **Push to external repos** via GitHub App tokens
- **Label-to-flow mapping** (e.g., `ralph` → `ralph_flow`)

### Workflows

- **Bug Fix Crew** (`bug-fix`): Triages, investigates, and fixes bugs with comprehensive regression testing
- **Feature Development Crew** (`feature-dev`): Implements features through ordered user stories with automated testing
- **Security Audit Crew** (`security-audit`): Scans for vulnerabilities and implements security fixes

### GitHub App Features

- **Multi-repository support**: Manage issues and projects across multiple repositories
- **Automated workflows**: Trigger flows by adding labels to issues
- **Push capability**: Commit and push to repos that have the app installed
- **Secure authentication**: GitHub App tokens with fine-grained permissions
- **Scalable architecture**: Redis caching + Celery workers for async processing

## Project Structure

```
coding_farm/
├── src/antfarm_crewai/
│   ├── crews/              # Crew implementations
│   │   ├── bug_fix/        # Bug fix workflow
│   │   ├── feature_dev/    # Feature development workflow
│   │   └── security_audit/ # Security audit workflow
│   ├── config/             # Shared configuration
│   └── tools/              # Custom tools
├── src/github_app/         # GitHub App integration
│   ├── auth.py            # JWT & token management
│   ├── config.py          # App configuration
│   ├── installation_manager.py  # Installation handling
│   ├── label_mapper.py    # Label-to-flow mapping
│   ├── multi_repo_manager.py    # Multi-repo operations + PUSH
│   ├── webhook_handler.py # Webhook processing
│   ├── tasks.py           # Celery tasks
│   └── app.py             # FastAPI webhook server
├── src/models/
│   ├── github_app.py      # Database models
│   └── migrations/        # Database migrations
├── docs/
│   ├── GITHUB_APP.md      # GitHub App documentation
│   └── GITHUB_APP_INTEGRATION.md  # Integration guide
├── main.py                 # CLI entry point
└── pyproject.toml          # Project dependencies
```

## Installation

### Prerequisites

- Python 3.10 or higher
- `uv` package manager (recommended)

### Setup

```bash
# Clone or navigate to the project
cd ~/projects/crewai

# Install dependencies
uv sync

# (Optional) Install in development mode
uv pip install -e .
```

An SSH alias is required for `github`:

```config
Host github
  Hostname github.com
  User git
```

## GitHub App Integration 🚀

Polycode includes GitHub App support for multi-repository project management with webhook-driven automation.

### Features

- **Multi-repo support**: Manage issues and projects across multiple repositories
- **Label-to-flow mapping**: Trigger workflows by adding labels (e.g., `ralph` → `ralph_flow`)
- **Push to external repos**: Commit and push changes to repos you don't own
- **Webhook automation**: Automatic flow execution when labels are added
- **Secure authentication**: GitHub App tokens instead of PATs

### GitHub App Installation

#### 1. Create GitHub App

1. Go to [GitHub App Settings](https://github.com/settings/apps/new)
2. Fill in basic information:
   - **App name**: "Polycode" (or your preferred name)
   - **Homepage URL**: Your project URL
   - **Webhook URL**: `https://your-domain.com/webhook/github`
   - **Webhook secret**: Generate a secure secret (save to `.env`)

3. Set permissions:

   ```
   Issues: Read & Write
   Projects: Read & Write
   Contents: Read & Write (required for push capability)
   Pull requests: Read & Write
   Metadata: Read (required)
   ```

4. Subscribe to events:
   - Issues
   - Push
   - Pull request
   - Installation

5. Click "Create GitHub App"
6. **Generate Private Key**:
   - Scroll to "Private keys" section
   - Click "Generate a private key"
   - Save the downloaded `.pem` file securely

#### 2. Configure Environment

Add to `.env`:

```bash
# GitHub App Configuration
GITHUB_APP_ID=123456                                    # From app settings page
GITHUB_APP_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA...
...
-----END RSA PRIVATE KEY-----"
GITHUB_APP_WEBHOOK_SECRET=your_webhook_secret_here

# Existing configuration
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=postgresql://user:pass@localhost/polycode
```

**Tip**: For `GITHUB_APP_PRIVATE_KEY`, copy the entire contents of the `.pem` file including the header/footer lines.

#### 3. Install Dependencies

```bash
# Add GitHub App dependencies
uv add pydantic-settings alembic

# Or with pip
pip install pydantic-settings alembic
```

#### 4. Run Database Migration

```bash
# Initialize Alembic (if not already done)
alembic init migrations

# Generate migration
alembic revision --autogenerate -m "Add GitHub App tables"

# Apply migration
alembic upgrade head
```

Or manually run the SQL from `src/models/migrations/github_app_001.py`.

#### 5. Start Services

```bash
# Terminal 1: Webhook server
uvicorn src.github_app.app:app --host 0.0.0.0 --port 8000

# Terminal 2: Celery worker (for async flow execution)
celery -A src.github_app.tasks worker --loglevel=info

# Terminal 3: (Optional) Celery beat for periodic tasks
celery -A src.github_app.tasks beat --loglevel=info

# Terminal 4: (Optional) Flower for monitoring
celery -A src.github_app.tasks flower
```

#### 6. Install App on Repositories

1. Go to your GitHub App settings page
2. Click "Install App" in the sidebar
3. Choose where to install:
   - All repositories (not recommended for production)
   - Only select repositories (recommended)
4. Select repositories to install on
5. Click "Install"

GitHub will send a webhook to your server automatically registering the installation.

#### 7. Create Label-to-Flow Mappings

Configure which labels trigger which flows:

```bash
# Map "ralph" label to "ralph_flow"
curl -X POST http://localhost:8000/mappings \
  -H "Content-Type: application/json" \
  -d '{
    "installation_id": 12345,
    "label_name": "ralph",
    "flow_name": "ralph_flow"
  }'

# Map "paid" label to "feature_development" for specific repos
curl -X POST http://localhost:8000/mappings \
  -H "Content-Type: application/json" \
  -d '{
    "installation_id": 12345,
    "label_name": "paid",
    "flow_name": "feature_development",
    "repo_pattern": "your-org/*",
    "priority": 1
  }'

# List existing mappings
curl http://localhost:8000/mappings
```

#### 8. Test the Integration

1. **Add a label** to an issue in a repo where the app is installed
2. **Check webhook logs**: `http://localhost:8000/health`
3. **Check Celery worker logs**: Flow should trigger automatically
4. **Verify execution**:

   ```bash
   # Check flow execution status
   curl http://localhost:8000/installations
   ```

### GitHub App Usage Examples

#### Push to External Repository

The GitHub App can push to repositories you don't own (if the app is installed):

```python
from src.github_app import MultiRepoProjectManager, GitHubAppAuth
from github import Github

# Get installation token
github_auth = GitHubAppAuth(app_id, private_key, redis_client)
token = github_auth.get_installation_token(installation_id)

# Create manager
github_client = Github(token)
manager = MultiRepoProjectManager(github_client)

# Push to ANY repo with app installed
manager.commit_and_push(
    repo_slug="external-org/external-repo",  # Not your repo!
    file_path="generated/code.py",
    content=generated_code,
    commit_message="Generate code automatically",
    branch="auto/generated",
    create_branch=True,
    create_pull_request=True
)
```

#### Trigger Flow via Label

```python
# 1. Create mapping (one-time setup)
mapper.create_mapping(
    installation_id=12345,
    label_name="ralph",
    flow_name="ralph_flow",
    repo_pattern="chainsquad/*"  # Optional: restrict to specific repos
)

# 2. Add "ralph" label to any issue in matching repos
# 3. Flow triggers automatically via webhook
# 4. Flow can push to external repos!
```

### GitHub App API Endpoints

| Endpoint                   | Method | Description                        |
| -------------------------- | ------ | ---------------------------------- |
| `/`                        | GET    | App info and status                |
| `/health`                  | GET    | Health check                       |
| `/webhook/github`          | POST   | GitHub webhook receiver            |
| `/installations`           | GET    | List all installations             |
| `/installations/{id}/sync` | POST   | Sync repositories for installation |
| `/mappings`                | GET    | List label-to-flow mappings        |
| `/mappings`                | POST   | Create new label mapping           |

### Webhook Testing

For local development, use ngrok:

```bash
# Install ngrok: https://ngrok.com/
ngrok http 8000

# Update GitHub App webhook URL to:
# https://your-ngrok-url.ngrok.io/webhook/github
```

### Monitoring

**Check installations:**

```bash
curl http://localhost:8000/installations
```

**Check flow executions:**

```python
from src.models.github_app import FlowExecution
from src.database import get_session

db = get_session()
executions = db.query(FlowExecution).filter(
    FlowExecution.status == "running"
).all()

for execution in executions:
    print(f"{execution.flow_name} in {execution.repo_slug}#{execution.issue_number}")
```

**Celery monitoring with Flower:**

```bash
celery -A src.github_app.tasks flower
# Open http://localhost:5555
```

### Custom Flow Handlers

Add custom flows in `src/github_app/tasks.py`:

```python
def execute_ralph_flow(
    installation_id, repo_slug, issue_number, issue_data,
    multi_repo_manager, db_session
):
    # Your custom logic
    code = generate_ralph_code(issue_data)

    # Push to repo
    multi_repo_manager.commit_and_push(
        repo_slug=repo_slug,
        file_path=f"ralph/issue_{issue_number}.py",
        content=code,
        commit_message=f"Ralph: {issue_data['title']}"
    )

    return {"status": "completed"}

# Register in flow_handlers dict
flow_handlers["ralph_flow"] = execute_ralph_flow
```

### Troubleshooting

| Issue                      | Solution                                            |
| -------------------------- | --------------------------------------------------- |
| Webhook 404                | Verify `WEBHOOK_PATH` matches GitHub App setting    |
| Signature validation fails | Check `GITHUB_APP_WEBHOOK_SECRET` matches           |
| Token generation fails     | Verify `GITHUB_APP_ID` and `GITHUB_APP_PRIVATE_KEY` |
| Can't push to repo         | Ensure app has `contents:write` permission          |
| Flow not triggered         | Check label mapping exists and is active            |
| Installation not found     | Sync repositories: `POST /installations/{id}/sync`  |

### GitHub App vs PAT

| Feature                | GitHub App          | Personal Access Token |
| ---------------------- | ------------------- | --------------------- |
| Multi-repo support     | ✅ Yes              | ❌ Manual setup       |
| Scoped permissions     | ✅ Per-installation | ❌ All-or-nothing     |
| Token expiry           | ✅ Auto-refresh     | ⚠️ Manual rotation    |
| Push to external repos | ✅ If app installed | ❌ Need their PAT     |
| Webhook automation     | ✅ Built-in         | ❌ Manual setup       |
| Security               | ✅ Fine-grained     | ⚠️ Broad access       |

### Additional Resources

- **Full documentation**: `docs/GITHUB_APP.md`
- **Integration guide**: `docs/GITHUB_APP_INTEGRATION.md`
- **GitHub Apps docs**: <https://docs.github.com/en/apps>

### Quick Start Checklist

- [ ] Create GitHub App at <https://github.com/settings/apps/new>
- [ ] Configure permissions (Issues, Projects, Contents, PRs)
- [ ] Generate private key and save to `.env`
- [ ] Set environment variables (`GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY`, `GITHUB_APP_WEBHOOK_SECRET`)
- [ ] Run database migration (`alembic upgrade head`)
- [ ] Start webhook server (`uvicorn src.github_app.app:app`)
- [ ] Start Celery worker (`celery -A src.github_app.tasks worker`)
- [ ] Install app on repositories
- [ ] Create label mappings via API
- [ ] Test by adding labels to issues

## Usage

### CLI Interface

```bash
# Run bug fix workflow
python main.py bug-fix "Fix login authentication failing with valid credentials"

# Run feature development workflow
python main.py feature-dev "Implement user profile management with avatar upload"

# Run security audit workflow
python main.py security-audit "/path/to/repository"
```

### Programmatic Usage

```python
from antfarm_crewai.crews import BugFixCrew, FeatureDevCrew, SecurityAuditCrew

# Bug Fix
bug_fix_crew = BugFixCrew()
result = bug_fix_crew.crew().kickoff(inputs={
    'task': 'Fix the login bug',
})

# Feature Development
feature_crew = FeatureDevCrew()
result = feature_crew.crew().kickoff(inputs={
    'task': 'Add dark mode support',
})

# Security Audit
security_crew = SecurityAuditCrew()
result = security_crew.crew().kickoff(inputs={
    'task': 'Audit the codebase for security vulnerabilities',
})
```

## Crew Architecture

### Bug Fix Crew

| Agent            | Role                            | Responsibility                                               |
| ---------------- | ------------------------------- | ------------------------------------------------------------ |
| **Triager**      | Bug Report Triager              | Analyzes bug reports, reproduces issues, classifies severity |
| **Investigator** | Root Cause Investigator         | Traces bugs to root cause and proposes fix approach          |
| **Setup**        | Environment Setup Specialist    | Creates bugfix branch and establishes baseline               |
| **Fixer**        | Bug Fix Implementation Engineer | Implements minimal, targeted fixes with regression tests     |
| **Verifier**     | Bug Fix Verification Specialist | Verifies fix correctness and completeness                    |
| **PR Creator**   | Pull Request Creator            | Creates clear, documented PRs with fix details               |

### Feature Development Crew

| Agent         | Role                            | Responsibility                                             |
| ------------- | ------------------------------- | ---------------------------------------------------------- |
| **Planner**   | Feature Planner                 | Decomposes tasks into ordered, executable user stories     |
| **Setup**     | Environment Setup Specialist    | Prepares environment, creates branch, establishes baseline |
| **Developer** | Feature Developer               | Implements features with high code quality and tests       |
| **Verifier**  | Implementation Verifier         | Quick sanity check of developer work                       |
| **Tester**    | Integration & E2E Test Engineer | Ensures features work together                             |
| **Reviewer**  | Code Review Specialist          | Reviews PRs for code quality and best practices            |

### Security Audit Crew

| Agent           | Role                                  | Responsibility                                      |
| --------------- | ------------------------------------- | --------------------------------------------------- |
| **Scanner**     | Security Scanner                      | Performs comprehensive security analysis            |
| **Prioritizer** | Security Finding Prioritizer          | Deduplicates, ranks, and groups findings            |
| **Setup**       | Security Environment Setup Specialist | Creates security branches and establishes baselines |
| **Fixer**       | Security Fix Implementation Engineer  | Implements minimal, targeted security fixes         |
| **Verifier**    | Security Fix Verification Specialist  | Verifies vulnerabilities are actually patched       |
| **Tester**      | Security Integration Tester           | Final integration testing and audit re-run          |
| **PR Creator**  | Security PR Creator                   | Creates comprehensive security PRs                  |

## Workflow Details

### Bug Fix Workflow

1. **Triage**: Analyze bug report, reproduce issue, classify severity
2. **Investigate**: Trace root cause and propose fix approach
3. **Setup**: Create bugfix branch, establish baseline
4. **Fix**: Implement minimal fix with regression test
5. **Verify**: Confirm fix addresses root cause
6. **PR**: Create pull request with comprehensive details

### Feature Development Workflow

1. **Plan**: Decompose task into ordered user stories
2. **Setup**: Prepare environment, create feature branch
3. **Implement**: Implement each story with tests (loop over all stories)
4. **Verify**: Quick sanity check of each story
5. **Test**: Integration and E2E testing
6. **PR**: Create pull request
7. **Review**: Code review with approval or changes

### Security Audit Workflow

1. **Scan**: Comprehensive security audit
2. **Prioritize**: Deduplicate and rank findings
3. **Setup**: Create security branch, establish baseline
4. **Fix**: Implement security fixes with regression tests (loop over all)
5. **Verify**: Confirm vulnerabilities are patched
6. **Test**: Final integration testing and audit re-run
7. **PR**: Create comprehensive security PR

## Comparison: Antfarm vs CrewAI Implementation

### Antfarm (Original)

- Custom orchestration system with fresh agent sessions
- SQL-based workflow state tracking
- Agent-specific workspace directories with SOUL/IDENTITY context
- Loop mechanism for iterative work (multiple stories/fixes)
- Cron-based polling for workflow advancement
- Custom tool integration via OpenClaw

### CrewAI Implementation (This Project)

- **Similarities**:
  - Same workflow structure (agents → tasks → sequential execution)
  - Same agent roles and responsibilities
  - Same task descriptions and expected outputs
  - YAML-based configuration for agents and tasks

- **Differences**:
  - Uses CrewAI framework instead of custom orchestration
  - Simpler state management (in-memory)
  - No built-in loop mechanism (simplified to single iteration)
  - Different tool integration approach
  - Uses CrewAI's process management instead of cron polling

## Key Design Decisions

### 1. Mapping Strategy

Each antfarm workflow maps to a CrewAI Crew:

- **Workflow** → **Crew**
- **Agent** → **Agent** (same roles and responsibilities)
- **Step** → **Task** (same inputs and expected outputs)

### 2. Configuration Files

Agent and task configurations follow antfarm's YAML structure:

- `agents.yaml`: Agent role, goal, backstory
- `tasks.yaml`: Task description, expected_output, agent assignment

### 3. Task Context

Tasks use CrewAI's context mechanism to pass data between agents:

```python
context=[self.previous_task()]
```

This mirrors antfarm's template variable system: `{{variable_name}}`

### 4. Simplified Looping

Antfarm's loop mechanism (for multiple stories/fixes) is simplified in this implementation to a single iteration. Full implementation would require custom CrewAI extensions or a separate orchestrator.

## Limitations

1. **No Loop Mechanism**: Feature dev and security audit workflows only process one story/fix
2. **No Persistence**: Workflow state is in-memory, not persisted to database
3. **No Cron Polling**: Workflows run synchronously, not via periodic polling
4. **Simplified Tool Integration**: Uses empty tools array, would need custom tools for git, testing, etc.

## Future Enhancements

1. **Custom Tools**: Implement git, file system, and testing tools
2. **Loop Extension**: Create CrewAI extension for iterative task execution
3. **State Persistence**: Add database-based workflow state tracking
4. **Async Execution**: Support asynchronous workflow execution
5. **Monitoring**: Add progress tracking and reporting
6. **Retry Logic**: Implement configurable retry mechanisms
7. **Error Handling**: More robust error recovery and escalation

## Development

### Adding Custom Tools

Create custom tools in `src/antfarm_crewai/tools/`:

```python
from crewai_tools import BaseTool

class GitTool(BaseTool):
    name: str = "GitTool"
    description: str = "Execute git commands"

    def _run(self, command: str) -> str:
        # Implementation
        pass
```

### Modifying Agent Behavior

Edit agent configuration in `config/agents.yaml`:

- Update role, goal, or backstory
- Adjust tools array
- Modify delegation settings

### Adding New Workflows

1. Create new crew directory: `src/antfarm_crewai/crews/your_workflow/`
2. Create `crew.py`, `config/agents.yaml`, `config/tasks.yaml`
3. Import in `src/antfarm_crewai/crews/__init__.py`
4. Add CLI entry point in `main.py`

## Testing

```bash
# Test bug fix workflow
python main.py bug-fix "Test bug report"

# Test feature development workflow
python main.py feature-dev "Test feature"

# Test security audit workflow
python main.py security-audit "/tmp/test-repo"
```

## Contributing

When contributing, maintain consistency with antfarm's workflow structure:

- Keep agent roles and responsibilities consistent
- Preserve task descriptions and expected outputs
- Follow the YAML configuration pattern
- Update documentation for any changes

## License

This project implements antfarm workflows using CrewAI framework. Original antfarm workflows are from <https://github.com/snarktank/ralph>.

## Resources

- [CrewAI Documentation](https://docs.crewai.com/)
- [Antfarm Workflows](~/.clawdbot/antfarm/workflows/)
- [CrewAI Quickstart](https://docs.crewai.com/en/quickstart)
- [CrewAI Concepts: Crews](https://docs.crewai.com/en/concepts/crews)

## Support

For issues or questions:

1. Check the [CrewAI documentation](https://docs.crewai.com/)
2. Review the original antfarm workflow files
3. Open an issue in the repository
