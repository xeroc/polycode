# Specify Flow Implementation Plan

## Overview

A new CrewAI flow that enables pair-programming-style specification refinement via GitHub issue comments. Developers converse with the AI to refine requirements, and when satisfied, the flow produces stories and automatically triggers the Ralph flow for implementation.

---

## Flow Lifecycle

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SPECIFY FLOW LIFECYCLE                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. TRIGGER                                                                 │
│     └── Issue labeled with `polycode:specify`                               │
│                                                                             │
│  2. START                                                                   │
│     ├── Read issue body + existing comments                                 │
│     ├── Generate initial clarifying questions                               │
│     └── Post as comment, pause flow                                         │
│                                                                             │
│  3. WAIT FOR INPUT (max 24hrs)                                              │
│     ├── Author comments → Resume flow                                       │
│     ├── Non-author comments → Ignore                                        │
│     ├── "LGTM" / "LFG" comment → COMPLETE                                   │
│     └── 24hr timeout → Auto-complete with current state                     │
│                                                                             │
│  4. RESUME                                                                  │
│     ├── Read new comments (author only)                                     │
│     ├── Generate follow-up or stories                                       │
│     ├── If clarifying needed → Post comment, return to WAIT                 │
│     └── If specification complete → PRODUCE STORIES                         │
│                                                                             │
│  5. PRODUCE STORIES                                                         │
│     ├── Run PlanCrew to generate stories                                    │
│     ├── Post stories summary as comment                                     │
│     ├── Add `polycode:implement` label                                      │
│     └── Trigger Ralph flow with full context                                │
│                                                                             │
│  6. CLEANUP                                                                 │
│     └── Remove from active_specify_flows table                              │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Configuration

| Setting          | Value                          | Notes                              |
| ---------------- | ------------------------------ | ---------------------------------- |
| Trigger label    | `polycode:specify`             | Starts the flow                    |
| Completion label | `polycode:implement`           | Added when flow hands off to Ralph |
| Timeout          | 24 hours                       | Auto-complete if author is silent  |
| Completion words | `LGTM`, `LFG`, `looks good`    | Case-insensitive, triggers handoff |
| Retry policy     | 3 retries, exponential backoff | On crew execution failures         |

---

## Database Schema

### Table: `active_specify_flows`

Tracks active flows for webhook routing.

```sql
CREATE TABLE active_specify_flows (
    id SERIAL PRIMARY KEY,
    flow_uuid TEXT NOT NULL UNIQUE,           -- repo_owner/repo_name/issue_number
    repo_owner TEXT NOT NULL,
    repo_name TEXT NOT NULL,
    issue_number INTEGER NOT NULL,
    issue_author TEXT NOT NULL,               -- GitHub username to filter comments
    project_config JSONB NOT NULL,            -- Full ProjectConfig for flow instantiation
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    last_comment_id BIGINT,                   -- Track last processed comment
    UNIQUE(repo_owner, repo_name, issue_number)
);

CREATE INDEX idx_specify_flows_uuid ON active_specify_flows(flow_uuid);
CREATE INDEX idx_specify_flows_repo ON active_specify_flows(repo_owner, repo_name, issue_number);
```

### Migration File

Location: `src/persistence/migrations/add_active_specify_flows.sql`

---

## File Structure

```
src/
├── flows/
│   └── specify/
│       ├── __init__.py
│       ├── flow.py              # Main SpecifyFlow with @persist, @start, @listen
│       ├── types.py             # SpecifyFlowState, SpecifyOutput types
│       └── module.py            # Module definition with FlowDef for registry
│
├── persistence/
│   └── migrations/
│       └── add_active_specify_flows.sql
│
├── tasks/
│   └── tasks.py                 # Add resume_specify_flow_task
│
├── github_app/
│   └── webhook_handler.py       # Add issue_comment event handling
│
└── bootstrap.py                 # Register specify module
```

---

## Types

### `src/flows/specify/types.py`

```python
"""Specify flow types."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SpecifyStage(str, Enum):
    """Stage of the specify flow."""

    STARTING = "starting"
    WAITING = "waiting"
    PROCESSING = "processing"
    COMPLETED = "completed"
    TIMEOUT = "timeout"
    ERROR = "error"


class SpecifyFlowState(BaseModel):
    """State persisted between specify flow steps."""

    # Identifiers
    flow_uuid: str
    repo_owner: str
    repo_name: str
    issue_number: int
    issue_author: str
    issue_title: str

    # Conversation state
    stage: SpecifyStage = SpecifyStage.STARTING
    conversation_history: list[dict[str, Any]] = Field(default_factory=list)
    last_processed_comment_id: int | None = None

    # Specification output
    specification_complete: bool = False
    completion_keyword: str | None = None  # "LGTM", "LFG", etc.

    # Timing
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    wait_started_at: datetime | None = None

    # Project config for crew instantiation
    project_config: dict[str, Any] = Field(default_factory=dict)

    # Error tracking
    retry_count: int = 0
    last_error: str | None = None

    @property
    def is_timed_out(self) -> bool:
        """Check if 24hr timeout has been exceeded."""
        if self.wait_started_at is None:
            return False
        elapsed = datetime.utcnow() - self.wait_started_at
        return elapsed.total_seconds() > 86400  # 24 hours


class SpecifyOutput(BaseModel):
    """Output from the specify flow."""

    stories: list[dict[str, Any]]
    repo_owner: str
    repo_name: str
    issue_number: int
    conversation_history: list[dict[str, Any]]
    specification_summary: str
```

---

## Flow Implementation

### `src/flows/specify/flow.py`

```python
"""Specify flow for pair-programming-style specification refinement."""

import logging
from datetime import datetime

from crewai import Flow, listen, persist, start

from crews.conversation_crew.conversation_crew import ConversationCrew
from crews.plan_crew.plan_crew import PlanCrew
from flows.base import FlowIssueManagement, KickoffIssue
from flows.specify.types import SpecifyFlowState, SpecifyOutput, SpecifyStage
from persistence.postgres import PostgresFlowPersistence

log = logging.getLogger(__name__)

COMPLETION_KEYWORDS = {"lgtm", "lfg", "looks good", "looks good to me", "ship it", "ready"}
MAX_RETRIES = 3


@persist(PostgresFlowPersistence)
class SpecifyFlow(Flow[SpecifyFlowState]):
    """Flow for refining specifications via GitHub issue comments."""

    @start()
    def kickoff(self, issue: KickoffIssue) -> SpecifyFlowState:
        """Initialize the specify flow from a labeled issue."""
        log.info(f"🎯 Starting specify flow for issue #{issue.id}")

        flow_uuid = f"{issue.repository.owner}/{issue.repository.name}/{issue.id}"

        state = SpecifyFlowState(
            flow_uuid=flow_uuid,
            repo_owner=issue.repository.owner,
            repo_name=issue.repository.name,
            issue_number=issue.id,
            issue_author=issue.repository.owner,  # TODO: Get actual author from issue
            issue_title=issue.title,
            stage=SpecifyStage.STARTING,
            conversation_history=[
                {"role": "user", "content": issue.body, "source": "issue_body"}
            ],
            project_config=issue.project_config.model_dump() if issue.project_config else {},
        )

        return state

    @listen(kickoff)
    def generate_initial_questions(self, state: SpecifyFlowState) -> SpecifyFlowState:
        """Generate initial clarifying questions from the issue."""
        log.info(f"❓ Generating initial questions for issue #{state.issue_number}")

        try:
            crew = ConversationCrew()
            result = crew.crew().kickoff(
                inputs={
                    "conversation_history": self._format_conversation(state.conversation_history),
                    "current_stage": "initial",
                }
            )

            # Post comment to issue
            comment_body = result.raw
            self._post_comment(state, comment_body)

            state.conversation_history.append(
                {"role": "assistant", "content": comment_body, "source": "flow"}
            )
            state.stage = SpecifyStage.WAITING
            state.wait_started_at = datetime.utcnow()
            state.updated_at = datetime.utcnow()

            # Register in active flows table
            self._register_active_flow(state)

            log.info(f"💬 Posted initial questions, waiting for response")

        except Exception as e:
            log.error(f"🚨 Failed to generate questions: {e}")
            state.stage = SpecifyStage.ERROR
            state.last_error = str(e)
            state.retry_count += 1

        return state

    @listen("resume")
    def process_new_comments(self, state: SpecifyFlowState) -> SpecifyFlowState:
        """Process new comments from the issue author."""
        log.info(f"📨 Processing new comments for issue #{state.issue_number}")

        # Check for timeout
        if state.is_timed_out:
            log.info(f"⏰ Flow timed out after 24 hours")
            state.stage = SpecifyStage.TIMEOUT
            return self._complete_flow(state)

        # Fetch new comments
        new_comments = self._fetch_new_comments(state)

        if not new_comments:
            log.info(f"📭 No new comments, returning to wait state")
            state.stage = SpecifyStage.WAITING
            return state

        # Add comments to history
        for comment in new_comments:
            state.conversation_history.append(
                {"role": "user", "content": comment["body"], "source": "comment", "id": comment["id"]}
            )
            state.last_processed_comment_id = comment["id"]

            # Check for completion keywords
            if self._contains_completion_keyword(comment["body"]):
                log.info(f"✅ Completion keyword detected: {comment['body']}")
                state.specification_complete = True
                state.completion_keyword = comment["body"].strip()
                return self._complete_flow(state)

        # Generate follow-up with ConversationCrew
        state.stage = SpecifyStage.PROCESSING

        try:
            crew = ConversationCrew()
            result = crew.crew().kickoff(
                inputs={
                    "conversation_history": self._format_conversation(state.conversation_history),
                    "current_stage": "refinement",
                }
            )

            # Post response
            comment_body = result.raw
            self._post_comment(state, comment_body)

            state.conversation_history.append(
                {"role": "assistant", "content": comment_body, "source": "flow"}
            )
            state.stage = SpecifyStage.WAITING
            state.wait_started_at = datetime.utcnow()
            state.updated_at = datetime.utcnow()

            log.info(f"💬 Posted follow-up, waiting for response")

        except Exception as e:
            log.error(f"🚨 Failed to process comments: {e}")
            state.last_error = str(e)
            state.retry_count += 1

            if state.retry_count >= MAX_RETRIES:
                log.error(f"🚨 Max retries exceeded, marking as error")
                state.stage = SpecifyStage.ERROR

        return state

    def _complete_flow(self, state: SpecifyFlowState) -> SpecifyFlowState:
        """Complete the flow and produce stories."""
        log.info(f"🏁 Completing specify flow for issue #{state.issue_number}")

        state.stage = SpecifyStage.COMPLETED
        state.updated_at = datetime.utcnow()

        # Run PlanCrew to generate stories
        try:
            crew = PlanCrew()
            result = crew.crew().kickoff(
                inputs={
                    "issue_title": state.issue_title,
                    "conversation_history": self._format_conversation(state.conversation_history),
                }
            )

            # Post stories summary
            stories_summary = self._format_stories_summary(result.stories)
            self._post_comment(state, f"## 📋 Generated Stories\n\n{stories_summary}")

            # Add polycode:implement label
            self._add_label(state, "polycode:implement")

            # Store output for Ralph flow
            state.metadata["output"] = SpecifyOutput(
                stories=[s.model_dump() for s in result.stories],
                repo_owner=state.repo_owner,
                repo_name=state.repo_name,
                issue_number=state.issue_number,
                conversation_history=state.conversation_history,
                specification_summary=result.summary if hasattr(result, "summary") else "",
            ).model_dump()

            # Unregister from active flows
            self._unregister_active_flow(state)

            log.info(f"✅ Specify flow complete, Ralph flow triggered")

        except Exception as e:
            log.error(f"🚨 Failed to complete flow: {e}")
            state.stage = SpecifyStage.ERROR
            state.last_error = str(e)

        return state

    # Helper methods

    def _format_conversation(self, history: list[dict]) -> str:
        """Format conversation history for crew input."""
        lines = []
        for entry in history:
            role = entry.get("role", "unknown")
            content = entry.get("content", "")
            lines.append(f"[{role.upper()}]: {content}")
        return "\n\n".join(lines)

    def _contains_completion_keyword(self, text: str) -> bool:
        """Check if text contains a completion keyword."""
        text_lower = text.lower().strip()
        return any(kw in text_lower for kw in COMPLETION_KEYWORDS)

    def _post_comment(self, state: SpecifyFlowState, body: str) -> None:
        """Post a comment to the issue."""
        # TODO: Implement with GitHubProjectManager
        log.info(f"📝 Would post comment to #{state.issue_number}: {body[:100]}...")

    def _fetch_new_comments(self, state: SpecifyFlowState) -> list[dict]:
        """Fetch new comments from the issue author."""
        # TODO: Implement with GitHubProjectManager
        # Filter by: author == state.issue_author
        # Filter by: id > state.last_processed_comment_id
        return []

    def _add_label(self, state: SpecifyFlowState, label: str) -> None:
        """Add a label to the issue."""
        # TODO: Implement with GitHubProjectManager
        log.info(f"🏷️ Would add label '{label}' to #{state.issue_number}")

    def _register_active_flow(self, state: SpecifyFlowState) -> None:
        """Register flow in active_specify_flows table."""
        # TODO: Implement with PostgresFlowPersistence
        pass

    def _unregister_active_flow(self, state: SpecifyFlowState) -> None:
        """Remove flow from active_specify_flows table."""
        # TODO: Implement with PostgresFlowPersistence
        pass

    def _format_stories_summary(self, stories: list) -> str:
        """Format stories for comment."""
        lines = []
        for i, story in enumerate(stories, 1):
            lines.append(f"### {i}. {story.title}")
            lines.append(f"{story.description}")
            lines.append("")
        return "\n".join(lines)
```

---

## Module Registration

### `src/flows/specify/module.py`

```python
"""Specify flow module definition."""

from flows.protocol import FlowDef
from flows.specify.flow import SpecifyFlow

specify_flow_module = FlowDef(
    name="specify",
    flow_class=SpecifyFlow,
    supported_labels=["polycode:specify"],
    description="Pair-programming-style specification refinement via GitHub comments",
)
```

### `src/flows/specify/__init__.py`

```python
"""Specify flow module."""

from flows.specify.flow import SpecifyFlow
from flows.specify.module import specify_flow_module
from flows.specify.types import SpecifyFlowState, SpecifyOutput, SpecifyStage

__all__ = ["SpecifyFlow", "SpecifyFlowState", "SpecifyOutput", "SpecifyStage", "specify_flow_module"]
```

---

## Webhook Handler Changes

### `src/github_app/webhook_handler.py`

Add `issue_comment` event handling:

```python
# Add to imports
from tasks.tasks import resume_specify_flow_task

# Add new event handler
@app.webhooks.handler("issue_comment")
async def handle_issue_comment(event: dict) -> dict:
    """Handle issue comment events for specify flow resumption."""

    action = event.get("action")
    if action not in ("created",):
        return {"status": "ignored", "reason": f"Action '{action}' not handled"}

    comment = event.get("comment", {})
    issue = event.get("issue", {})
    repository = event.get("repository", {})

    repo_owner = repository.get("owner", {}).get("login")
    repo_name = repository.get("name")
    issue_number = issue.get("number")
    comment_author = comment.get("user", {}).get("login")
    comment_id = comment.get("id")

    log.info(f"💬 Issue comment #{comment_id} on {repo_owner}/{repo_name}#{issue_number}")

    # Check if there's an active specify flow for this issue
    from persistence.postgres import get_active_specify_flow

    active_flow = get_active_specify_flow(repo_owner, repo_name, issue_number)
    if not active_flow:
        log.info(f"📭 No active specify flow for issue #{issue_number}")
        return {"status": "ignored", "reason": "No active specify flow"}

    # Check if comment is from the issue author
    if comment_author != active_flow["issue_author"]:
        log.info(f"🚫 Comment from non-author '{comment_author}', ignoring")
        return {"status": "ignored", "reason": "Comment not from issue author"}

    # Queue task to resume the flow
    resume_specify_flow_task.delay(
        flow_uuid=active_flow["flow_uuid"],
        comment_id=comment_id,
    )

    return {"status": "queued", "flow_uuid": active_flow["flow_uuid"]}
```

---

## Celery Task

### `src/tasks/tasks.py`

Add new task:

```python
@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def resume_specify_flow_task(self, flow_uuid: str, comment_id: int) -> dict:
    """Resume a specify flow after a new comment."""

    log.info(f"▶️ Resuming specify flow {flow_uuid} for comment #{comment_id}")

    try:
        from flows.specify.flow import SpecifyFlow
        from persistence.postgres import load_flow_state

        state = load_flow_state(flow_uuid)
        if not state:
            log.error(f"🚨 Flow state not found: {flow_uuid}")
            return {"status": "error", "reason": "State not found"}

        flow = SpecifyFlow()
        result = flow.process_new_comments(state)

        return {"status": "success", "stage": result.stage}

    except Exception as e:
        log.error(f"🚨 Failed to resume flow: {e}")
        self.retry(exc=e)
        return {"status": "error", "reason": str(e)}
```

---

## Persistence Functions

### `src/persistence/postgres.py`

Add helper functions:

```python
def get_active_specify_flow(repo_owner: str, repo_name: str, issue_number: int) -> dict | None:
    """Get active specify flow by repository and issue."""
    with SessionLocal() as session:
        result = session.execute(
            text("""
                SELECT * FROM active_specify_flows
                WHERE repo_owner = :owner AND repo_name = :name AND issue_number = :issue
            """),
            {"owner": repo_owner, "name": repo_name, "issue": issue_number}
        ).fetchone()
        return dict(result._mapping) if result else None


def register_active_specify_flow(state: SpecifyFlowState) -> None:
    """Register an active specify flow."""
    with SessionLocal() as session:
        session.execute(
            text("""
                INSERT INTO active_specify_flows
                (flow_uuid, repo_owner, repo_name, issue_number, issue_author, project_config, last_comment_id)
                VALUES (:uuid, :owner, :name, :issue, :author, :config, :comment_id)
                ON CONFLICT (flow_uuid) DO UPDATE SET
                    updated_at = NOW(),
                    last_comment_id = :comment_id
            """),
            {
                "uuid": state.flow_uuid,
                "owner": state.repo_owner,
                "name": state.repo_name,
                "issue": state.issue_number,
                "author": state.issue_author,
                "config": json.dumps(state.project_config),
                "comment_id": state.last_processed_comment_id,
            }
        )
        session.commit()


def unregister_active_specify_flow(flow_uuid: str) -> None:
    """Remove an active specify flow."""
    with SessionLocal() as session:
        session.execute(
            text("DELETE FROM active_specify_flows WHERE flow_uuid = :uuid"),
            {"uuid": flow_uuid}
        )
        session.commit()
```

---

## Ralph Flow Modifications

### Changes to `src/flows/ralph/flow.py`

1. **Remove PlanCrew execution** from the ralph flow
2. **Accept pre-generated stories** from state (passed by specify flow)
3. **Skip planning stage** if stories are already provided

```python
@start()
def kickoff(self, issue: KickoffIssue) -> RalphLoopState:
    """Initialize the ralph flow."""

    # Check if stories are provided from specify flow
    pre_generated_stories = issue.project_config.extra.get("stories") if issue.project_config else None

    state = RalphLoopState(
        # ... existing initialization ...
        stories=pre_generated_stories or [],  # Use pre-generated if available
        skip_planning=bool(pre_generated_stories),
    )

    return state

@listen(kickoff)
def plan_or_skip(self, state: RalphLoopState) -> RalphLoopState:
    """Run PlanCrew or skip if stories already provided."""

    if state.skip_planning:
        log.info(f"⏭️ Skipping planning, using pre-generated stories")
        return state

    # ... existing PlanCrew logic ...
```

---

## Bootstrap Registration

### `src/bootstrap.py`

```python
# Add specify flow module to registry
from flows.specify.module import specify_flow_module

# In module loading:
flow_registry.register(specify_flow_module)
```

---

## Testing Strategy

### Unit Tests

1. **`test_specify_flow_types.py`**

   - Test `SpecifyFlowState.is_timed_out` with various timestamps
   - Test completion keyword detection
   - Test conversation history formatting

2. **`test_specify_flow.py`**

   - Test kickoff initialization
   - Test comment filtering (author only)
   - Test completion keyword handling
   - Test timeout behavior
   - Test retry logic

3. **`test_webhook_issue_comment.py`**
   - Test comment routing to active flows
   - Test non-author comment filtering
   - Test task queueing

### Integration Tests

1. **End-to-end specify flow**
   - Label issue → flow starts → comment posted
   - Author comments → flow resumes → follow-up posted
   - Author says "LGTM" → stories generated → label added → Ralph triggered

---

## Implementation Order

1. ✅ Types (`src/flows/specify/types.py`)
2. ✅ Module (`src/flows/specify/module.py`, `__init__.py`)
3. ✅ Flow skeleton (`src/flows/specify/flow.py` with TODOs)
4. ✅ Database migration (`src/persistence/migrations/add_active_specify_flows.sql`)
5. ✅ Persistence helpers (`src/persistence/postgres.py`)
6. ✅ Webhook handler (`src/github_app/webhook_handler.py`)
7. ✅ Celery task (`src/tasks/tasks.py`)
8. ✅ Bootstrap registration (`src/bootstrap.py`)
9. ✅ Ralph flow modifications (`src/flows/ralph/flow.py`)
10. ✅ Tests
11. ✅ Integration testing

---

## Success Criteria

- [ ] Flow starts when `polycode:specify` label is added
- [ ] Initial clarifying questions posted as comment
- [ ] Flow pauses and waits for author input
- [ ] Flow resumes when author comments (not others)
- [ ] Follow-up questions posted as needed
- [ ] Flow completes on "LGTM" / "LFG" keywords
- [ ] Stories generated via PlanCrew
- [ ] `polycode:implement` label added on completion
- [ ] Ralph flow triggered automatically
- [ ] Flow times out after 24 hours
- [ ] Retries on transient failures
- [ ] All tests passing
- [ ] Lint and type check clean
