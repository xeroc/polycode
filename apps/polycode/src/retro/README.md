# Retro Module - Continuous Improvement via Retrospectives

LLM-powered retrospective system that stores learnings with git-notes and indexes in PostgreSQL for pattern analysis.

## Overview

Retrospectives are automatically generated after each flow execution, capturing what worked, what failed, root causes, and actionable improvements. This feeds a continuous improvement loop where past learnings inform future executions.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Flow Execution (Ralph/Feature)                 │
│                         │                                  │
│                         ▼                                  │
│              ┌─────────────────┐                         │
│              │  Retro Generation │                         │
│              │  (CrewAI LLM)    │                         │
│              └────────┬────────┘                         │
│                       │                                   │
│       ┌───────────────┴───────────────┐               │
│       │                              │               │
│       ▼                              ▼               │
│  ┌─────────────┐                 ┌──────────────┐ │
│  │  git-notes  │                 │  PostgreSQL   │ │
│  │  (Storage)   │                 │  (Query)      │ │
│  └─────────────┘                 └──────────────┘ │
│                                                   │
│       ┌───────────────────────────────┴───────────────┐ │
│       │         Pattern Analyzer                  │ │
│       │         (Recurring Issues)               │ │
│       └───────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### Data Models (`retro/types.py`)

```python
RetroEntry    # Complete retrospective structure
RetroQuery    # Query parameters for database
ActionableItem  # Single improvement suggestion
```

**RetroEntry Fields:**

- `commit_sha`: Git commit reference
- `flow_id`: Flow execution UUID
- `story_id`: Story identifier (optional)
- `story_title`: Story title (optional)
- `repo_owner`, `repo_name`: Repository context
- `retro_type`: success/failure/partial/anomaly
- `what_worked`: List of successful patterns
- `what_failed`: List of failures
- `root_causes`: List of root cause analysis
- `actionable_improvements`: List of improvements with priorities
- `time_to_completion_seconds`: Duration
- `retry_count`: Iteration count
- `test_coverage_impact`: Coverage change percentage
- `build_duration_ms`, `test_duration_ms`: Performance metrics

### Git-Notes Integration (`retro/git_notes.py`)

Stores retrospectives as git notes attached to commits:

```python
from retro import GitNotes

notes = GitNotes(repo_path="/path/to/repo")

# Add retro to current commit
notes.add(retro=retro_entry, force=False)

# Show retro for a commit
retro = notes.show(commit_sha="abc123")

# List all retros with notes
shas = notes.list_all()

# Push notes to remote
notes.push(remote="origin")
```

**Notes Ref:** `refs/notes/retros` (custom ref, separate from default)

### PostgreSQL Storage (`retro/persistence.py`)

Mirrors git-notes for querying and aggregation:

```python
from retro.persistence import RetroStore, init_db

# Initialize database
init_db(DATABASE_URL)

# Create store
store = RetroStore(SessionLocal)
store.create_tables()

# Store retro
store.store(retro=retro_entry)

# Query retros
results = store.query(
    RetroQuery(
        repo_owner="chainsquad",
        repo_name="chaoscraft",
        retro_type="failure",
        limit=10
    )
)
```

**Table Schema:**

```sql
CREATE TABLE retrospectives (
    id SERIAL PRIMARY KEY,
    commit_sha VARCHAR(40),
    flow_id UUID,
    story_id INT,
    story_title VARCHAR,
    repo_owner VARCHAR,
    repo_name VARCHAR,
    retro_type VARCHAR,
    what_worked JSONB,
    what_failed JSONB,
    root_causes JSONB,
    actionable_improvements JSONB,
    time_to_completion_seconds INT,
    retry_count INT,
    test_coverage_impact FLOAT,
    build_duration_ms INT,
    test_duration_ms INT,
    created_at TIMESTAMP
);
```

### LLM-Powered Retro Crew (`retro/crews/retro_crew/`)

CrewAI crew that generates structured retrospectives:

**Agents:**

- `retro_analyst`: Analyzes execution data, identifies patterns, suggests improvements

**Tasks:**

- `analyze_execution`: Extract successes and failures
- `generate_improvements`: Propose actionable changes
- `finalize_retro`: Structure as RetroEntry with proper retro_type

```python
from retro.crews.retro_crew import RetroCrew

crew = RetroCrew()
result = crew.crew().kickoff(
    inputs={
        "execution_data": "...",
        "error_history": "...",
        "metrics": {...}
    }
)
retro = result.pydantic  # RetroEntry
```

### Pattern Analyzer (`retro/analyzer.py`)

Analyzes historical retros to identify trends:

```python
from retro import PatternAnalyzer

analyzer = PatternAnalyzer(store=retro_store)

# Recent trends
trends = analyzer.analyze_recent_trends(limit=20)

# Context for next flow
context = analyzer.generate_context_injection(
    repo_owner="chainsquad",
    repo_name="chaoscraft",
    limit=5
)

# Improvement suggestions
suggestions = analyzer.suggest_improvements_from_patterns(limit=10)
```

**Output:**

- Common failure patterns
- Success factors
- Performance trends (duration, retries)
- Build failure rates
- Recurring issues

## Integration with Flows

### Option 1: Per-Story Retros (Ralph Loop)

Hook into `_commit_changes()` in `flowbase.py`:

```python
# In flowbase.py

from retro import GitNotes, RetroStore, init_db

class FlowIssueManagement(Flow[T]):
    def _commit_changes(self, title: str, body="", footer=""):
        # ... existing commit logic ...

        commit = repo.index.commit(commit_message)
        commit_sha = commit.hexsha

        # Generate and store retro
        retro = self._generate_retro_for_commit(commit_sha, title)
        notes = GitNotes(self.state.repo)
        notes.add(retro=retro)

        # Also store in Postgres for querying
        init_db(DATABASE_URL)
        store = RetroStore(SessionLocal)
        store.create_tables()
        store.store(retro=retro)

        return commit

    def _generate_retro_for_commit(self, commit_sha: str, title: str) -> RetroEntry:
        """Generate retro entry using LLM crew."""
        # Collect execution data
        execution_data = {
            "commit_sha": commit_sha,
            "title": title,
            "build_success": self.state.build_success,
            "test_success": self.state.test_success,
            "retry_count": len(story.errors) if story else 0,
            "errors": story.errors if story else [],
        }

        # Run retro crew
        from retro.crews.retro_crew import RetroCrew
        crew = RetroCrew()
        result = crew.crew().kickoff(inputs=execution_data)
        return result.pydantic
```

**Trigger Points:**

- After each story commit in Ralph Loop
- After each feature commit in Feature Flow
- On flow completion (summary retro)

### Option 2: Flow-Completion Retro

Hook into `_cleanup_worktree()`:

```python
# In flowbase.py

class FlowIssueManagement(Flow[T]):
    def _cleanup_worktree(self):
        # ... existing cleanup logic ...

        # Generate flow-level retro
        retro = self._generate_flow_retro()
        notes = GitNotes(self.state.repo)
        notes.add(retro=retro)

        return

    def _generate_flow_retro(self) -> RetroEntry:
        """Generate flow-level retrospective."""
        from retro.crews.retro_crew import RetroCrew
        crew = RetroCrew()
        result = crew.crew().kickoff(
            inputs={
                "flow_id": str(self.state.flow_id),
                "all_stories": self.state.stories,
                "build_results": self.state.build_success,
                "test_results": self.state.test_success,
            }
        )
        return result.pydantic
```

### Option 3: Pre-Flow Context Injection

Inject past retros as context for next flow:

```python
# In flowbase.py

class FlowIssueManagement(Flow[T]):
    @start()
    def setup(self):
        self._setup()

        # Load past retros for context
        from retro import PatternAnalyzer, init_db
        init_db(DATABASE_URL)
        analyzer = PatternAnalyzer(RetroStore(SessionLocal))

        context = analyzer.generate_context_injection(
            repo_owner=self.state.repo_owner,
            repo_name=self.state.repo_name,
            limit=5
        )

        # Store context for agent access
        self.store("flow_context", context, scope=self.state.memory_prefix)

        self.pickup_issue()
```

## Environment Variables

```
DATABASE_URL=postgresql://user:password@localhost:5432/polycode
OPENAI_API_KEY=sk-...  # For retro crew LLM
```

## Usage Examples

### Generate Retro for Current Commit

```python
from retro import GitNotes, RetroStore, init_db
from retro.types import RetroEntry

# Initialize
init_db(DATABASE_URL)
store = RetroStore(SessionLocal)
notes = GitNotes("/path/to/repo")

# Generate retro (e.g., after commit in Ralph Loop)
retro = RetroEntry(
    commit_sha="abc123",
    flow_id="uuid-here",
    retro_type="success",
    what_worked=[
        "Tests passed on first attempt",
        "Build completed under 30s",
    ],
    what_failed=[],
    root_causes=[],
    actionable_improvements=[
        ActionableItem(
            title="Add more test cases",
            description="Cover edge cases found during this run",
            priority="medium",
        )
    ],
)

# Store
notes.add(retro=retro)
store.store(retro=retro)
```

### Query Past Retros

```python
from retro import PatternAnalyzer, init_db

init_db(DATABASE_URL)
analyzer = PatternAnalyzer(RetroStore(SessionLocal))

# Recent failures
failures = analyzer.analyze_recent_trends(limit=10)
print(failures["common_failures"])

# Top issues
top_issues = analyzer.store.get_top_issues(limit=5)
print(top_issues)

# Generate suggestions
suggestions = analyzer.suggest_improvements_from_patterns(limit=20)
for suggestion in suggestions:
    print(f"- {suggestion}")
```

### View Retro in Git

```bash
# Show retro for specific commit
git notes show refs/notes/retros abc123

# List all retros
git notes --ref refs/notes/retros list

# Push retros to remote
git push origin refs/notes/retros

# Pull retros from remote
git fetch origin refs/notes/retros
git notes merge origin/refs/notes/retros
```

## Benefits

1. **Transportability**: Git-notes travel with the repo, no external dependencies
2. **Queryability**: PostgreSQL enables complex queries and aggregation
3. **Continuous Learning**: LLM analyzes patterns to generate actionable insights
4. **No Bloat**: Retro metadata doesn't clutter commit messages
5. **Team Sync**: Push/pull retros like any other git ref

## Future Enhancements

- [ ] Dashboard UI for visualizing retro trends
- [ ] Automated improvement tracking (mark suggestions as implemented)
- [ ] Correlation analysis (e.g., test failure ↔ build failure)
- [ ] Cross-repo pattern detection (global learnings)
- [ ] Retro-driven test generation (target known failure paths)

## Dependencies

Added to `pyproject.toml`:

```toml
[project]
dependencies = [
    "crewai",
    "pydantic",
    "sqlalchemy",
    "psycopg2-binary",
]

[project.optional-dependencies]
# gitpython3 included in standard library
```
