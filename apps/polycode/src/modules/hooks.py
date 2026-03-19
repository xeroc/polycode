"""Flow orchestration event specifications.

Uses pluggy (already a dependency of crewai via pytest) for hook management.

Events focus on flow orchestration (git, PRs, cleanup) - NOT crew-level lifecycle.
CrewAI already provides @before_kickoff and @after_kickoff decorators for crews.

Modules register hook implementations via @hookimpl decorator.
"""

from enum import StrEnum
from typing import TYPE_CHECKING

import pluggy

if TYPE_CHECKING:
    pass

POLYCODE_NS = "polycode"

hookspec = pluggy.HookspecMarker(POLYCODE_NS)
hookimpl = pluggy.HookimplMarker(POLYCODE_NS)


class FlowEvent(StrEnum):
    """Flow orchestration events - plugins hook into these.

    Crew-level lifecycle (PRE_PLAN, POST_PLAN, etc.) is handled by CrewAI's
    @before_kickoff and @after_kickoff decorators. These events are for
    orchestration concerns outside of crews.

    Use the 'label' parameter for context (e.g., "plan", "implement").
    """

    FLOW_START = "flow_start"
    FLOW_COMPLETE = "flow_complete"
    FLOW_ERROR = "flow_error"

    GIT_COMMIT = "git_commit"
    GIT_PUSH = "git_push"

    PR_CREATED = "pr_created"
    PR_MERGED = "pr_merged"

    ISSUE_UPDATED = "issue_updated"
    WORKTREE_CLEANUP = "worktree_cleanup"

    CHECKLIST_POSTED = "checklist_posted"
    CHECKLIST_UPDATED = "checklist_updated"


class FlowHookSpec:
    """Hook specifications for flow orchestration events.

    Implementations use the @hookimpl decorator from modules/hooks.py.

    Example:

        from modules.hooks import FlowEvent, hookimpl

        class MyHooks:
            @hookimpl
            def on_flow_event(self, event, flow_id, state, result=None, label=""):
                if event == FlowEvent.GIT_COMMIT:
                    print(f"Commit {result} made in flow {flow_id}")
                if event == FlowEvent.FLOW_COMPLETE:
                    print(f"Flow {flow_id} finished successfully")
    """

    @hookspec
    def on_flow_event(
        self,
        event: FlowEvent,
        flow_id: str,
        state: object,
        result: object | None = None,
        label: str = "",
    ) -> None:
        """Called at each flow orchestration event.

        Args:
            event: Which event is firing.
            flow_id: Unique flow identifier.
            state: The flow's state model (read-only reference).
            result: Event-specific result (e.g., commit sha, pr url).
            label: Optional context label (e.g., "plan", "implement").
        """
        ...

    @hookspec
    def on_flow_error(self, flow_id: str, state: object, error: Exception) -> bool | None:
        """Called on unhandled flow exception.

        Return True to suppress the exception and allow flow to continue.
        Return None or False to let the exception propagate.
        """
        ...


def get_plugin_manager() -> pluggy.PluginManager:
    """Create and configure a plugin manager with hook specs."""
    pm = pluggy.PluginManager(POLYCODE_NS)
    pm.add_hookspecs(FlowHookSpec)
    return pm
