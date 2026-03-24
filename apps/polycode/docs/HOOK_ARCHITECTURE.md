# Simplified Hook Architecture

> **Status**: Implemented
> **Last Updated**: 2026-03-19

## Overview

Polycode now uses a simplified event-based hook system with **5 events** instead of 24 phases.

### Key Changes

1. **FlowPhase → FlowEvent**: Renamed and simplified from 24 phases to 5 events
2. **PolycodeCrew base class**: All crews extend this to auto-emit CREW_FINISHED events
3. **Label-based filtering**: Plugins filter by `event + label` instead of specific phases
4. **Delegated operations**: Git, PR, and checklist operations moved to plugin hooks

---

## Flow Events

```python
class FlowEvent(StrEnum):
    """Flow lifecycle events."""

    FLOW_STARTED = "flow_started"    # Flow initialization
    FLOW_FINISHED = "flow_finished"  # Flow completion (after verify)
    FLOW_ERROR = "flow_error"        # Unhandled exception

    CREW_FINISHED = "crew_finished"  # Crew execution complete
    STORY_COMPLETED = "story_completed"  # Single story implemented
```

### Event Labels

Labels provide context for filtering:

| Event             | Label Examples                      | Purpose              |
| ----------------- | ----------------------------------- | -------------------- |
| `FLOW_STARTED`    | `"ralph"`, `"feature_dev"`          | Identify which flow  |
| `FLOW_FINISHED`   | `"ralph"`, `"feature_dev"`          | Identify which flow  |
| `CREW_FINISHED`   | `"plan"`, `"implement"`, `"review"` | Identify which crew  |
| `STORY_COMPLETED` | `story.id`, `story.title`           | Identify which story |

---

## Hook Signature

```python
@hookimpl
def on_flow_event(
    self,
    event: FlowEvent,
    flow_id: str,
    state: object,
    result: object | None = None,
    label: str = "",
) -> None:
    """Handle flow lifecycle events.

    Args:
        event: Which event is firing
        flow_id: Unique flow identifier
        state: Flow state model (read-only reference)
        result: Event-specific result (e.g., Story object, crew output)
        label: Context label (e.g., "plan", "implement", "ralph")
    """
```

---

## PolycodeCrewMixin Base Class

All Polycode crews extend `PolycodeCrewMixin` to automatically emit `CREW_FINISHED` events:

```python
from crews.base import PolycodeCrewMixin

@CrewBase
class PlanCrew(PolycodeCrewMixin):
    """Planning crew."""

    crew_label = "plan"  # Used in CREW_FINISHED event

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def planner(self) -> Agent:
        return Agent(config=self.agents_config["planner"])  # type: ignore[index]

    @task
    def plan_task(self) -> Task:
        return Task(config=self.tasks_config["plan_task"])  # type: ignore[index]

    @crew
    def crew(self) -> Crew:
        return Crew(agents=self.agents, tasks=self.tasks)
```

The `@after_kickoff` hook in `PolycodeCrewMixin` automatically emits:

```python
FlowEvent.CREW_FINISHED, label="plan", result=crew_output
```

---

## Flow Structure (Ralph Loop Example)

```python
@start()
def setup(self):
    """Initialize flow."""
    self._emit(FlowEvent.FLOW_STARTED, label="ralph")
    self._setup()  # Worktree, discover AGENTS.md, discover build_cmd

@listen(setup)
def plan(self):
    """Plan stories."""
    result = PlanCrew().crew().kickoff(...)
    # PlanCrew emits CREW_FINISHED(label="plan") via @after_kickoff
    self.state.stories = result.pydantic.stories

@listen(plan)
def implement(self):
    """Implement each story."""
    for story in unfinished_stories:
        result = RalphCrew().crew().kickoff(...)
        # RalphCrew emits CREW_FINISHED(label="implement") via @after_kickoff

        self._test()  # Verify tests pass

        story.completed = True
        self._emit(FlowEvent.STORY_COMPLETED, result=story, label=str(story.id))
        # Hooks handle: commit, push, update checklist

@listen(implement)
def verify_build(self):
    """Final verification."""
    self._build()
    self._test()

    self._emit(FlowEvent.FLOW_FINISHED, label="ralph")
    # Hooks handle: create PR, merge PR, final checklist update, cleanup worktree
```

---

## Plugin Hook Implementations

### Gitcore Hooks (Git Operations)

```python
class GitcoreHooks:
    @hookimpl
    def on_flow_event(self, event, flow_id, state, result=None, label=""):
        if event == FlowEvent.STORY_COMPLETED:
            # Commit and push changes
            git_ops = GitOperations.from_flow_state(state, None)
            commit = git_ops.commit(title, body, footer)
            git_ops.push()

        elif event == FlowEvent.FLOW_FINISHED:
            # Cleanup worktree
            git_ops = GitOperations.from_flow_state(state, None)
            git_ops.cleanup()
```

### Project Manager Hooks (GitHub Operations)

```python
class ProjectManagerHooks:
    @hookimpl
    def on_flow_event(self, event, flow_id, state, result=None, label=""):
        if event == FlowEvent.FLOW_STARTED:
            # Post initial planning comment
            pass

        elif event == FlowEvent.STORY_COMPLETED:
            # Update checklist item
            self._update_checklist(state, pm, result)

        elif event == FlowEvent.FLOW_FINISHED:
            # Create PR
            pr = github_repo.create_pull(...)
            state.pr_url = pr.html_url

            # Merge PR (if approved)
            pm.merge_pull_request(pr.number)

            # Final checklist update
            self._update_checklist(state, pm, merged=True)

            # Update issue status to Done
            pm.update_issue_status(issue_id, "Done")
```

---

## Comparison: Before vs After

### Before (24 Phases)

```python
# flowbase.py had 24 phases
PRE_SETUP, POST_SETUP
PRE_PLAN, POST_PLAN
PRE_IMPLEMENT, POST_IMPLEMENT_STORY, POST_IMPLEMENT
PRE_COMMIT, POST_COMMIT
PRE_PUSH, POST_PUSH
PRE_PR, POST_PR
PRE_TEST, POST_TEST
PRE_REVIEW, POST_REVIEW
PRE_MERGE, POST_MERGE
PRE_CLEANUP, POST_CLEANUP
ON_ERROR, ON_COMPLETE
PRE_PLANNING_COMMENT, POST_PLANNING_COMMENT
PRE_UPDATE_CHECKLIST, POST_UPDATE_CHECKLIST

# flowbase.py had delegated methods
def _commit_changes(...)
def _push_repo(...)
def _create_pr(...)
def _merge_branch(...)
def _cleanup_worktree(...)
def _post_planning_checklist(...)
def _update_planning_checklist(...)
```

### Current Implementation

```python
# modules/hooks.py has 5 events
FLOW_STARTED
FLOW_FINISHED
FLOW_ERROR
CREW_FINISHED
STORY_COMPLETED

# flows/base.py (FlowIssueManagement)
def _prepare_work_tree()  # Worktree setup
def _discover_agents_md()  # Find AGENTS.md for build/test
def _emit()               # Hook emission

# crews/base.py (PolycodeCrewMixin)
def emit_crew_finished()  # Auto-emit CREW_FINISHED via @after_kickoff

# gitcore/ops.py (GitOperations)
def commit_and_push()      # Commits and pushes via hooks
def cleanup()               # Removes worktree
```

**Lines of code reduced**: ~150 lines removed from flowbase.py, delegated operations moved to plugins

---

## Benefits

1. **Simpler for plugin developers**: 5 events vs 24 phases to understand
2. **Less code to maintain**: Delegated methods moved to plugins
3. **More flexible**: Free-form labels instead of rigid phase names
4. **Better separation**: Flow orchestrates, plugins execute
5. **Easier to extend**: Add new labels without changing enums

---

## Migration Guide

### For Existing Plugins

Old hook pattern:

```python
@hookimpl
def on_flow_phase(self, phase, flow_id, state, result=None):
    if phase == FlowPhase.POST_COMMIT:
        self.handle_commit(result)
```

New hook pattern:

```python
@hookimpl
def on_flow_event(self, event, flow_id, state, result=None, label=""):
    if event == FlowEvent.STORY_COMPLETED:
        self.handle_story_completed(result)
```

### For Existing Crews

Old crew pattern:

```python
@CrewBase
class PlanCrew:
    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def planner(self) -> Agent:
        return Agent(config=self.agents_config["planner"])
```

New crew pattern (extend PolycodeCrew):

```python
from crews.base import PolycodeCrew

@CrewBase
class PlanCrew(PolycodeCrew):
    crew_label = "plan"  # Add this line

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def planner(self) -> Agent:
        return Agent(config=self.agents_config["planner"])
```

---

## See Also

- `src/modules/hooks.py` - Event definitions and hook specs
- `src/crews/base.py` - PolycodeCrew base class
- `src/flowbase.py` - Simplified flow base class
- `src/ralph/__init__.py` - Example flow using new architecture
- `src/gitcore/hooks.py` - Git operations hooks
- `src/project_manager/hooks.py` - GitHub operations hooks
