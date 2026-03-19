"""Flow lifecycle hook specifications.

Uses pluggy (already a dependency of crewai via pytest) for hook management.

Hook phases map to specific methods in FlowIssueManagement.
Modules register hook implementations via @hookimpl decorator.
"""

from enum import StrEnum
from typing import TYPE_CHECKING

import pluggy

POLYCODE_NS = "polycode"

if TYPE_CHECKING:
    pass

hookspec = pluggy.HookspecMarker(POLYCODE_NS)
hookimpl = pluggy.HookimplMarker(POLYCODE_NS)


class FlowPhase(StrEnum):
    """Flow lifecycle phases in execution order."""

    PRE_SETUP = "pre_setup"
    POST_SETUP = "post_setup"

    PRE_PLAN = "pre_plan"
    POST_PLAN = "post_plan"

    PRE_IMPLEMENT = "pre_implement"
    POST_IMPLEMENT_STORY = "post_implement_story"
    POST_IMPLEMENT = "post_implement"

    PRE_COMMIT = "pre_commit"
    POST_COMMIT = "post_commit"

    PRE_PUSH = "pre_push"
    POST_PUSH = "post_push"

    PRE_PR = "pre_pr"
    POST_PR = "post_pr"

    PRE_TEST = "pre_test"
    POST_TEST = "post_test"

    PRE_REVIEW = "pre_review"
    POST_REVIEW = "post_review"

    PRE_MERGE = "pre_merge"
    POST_MERGE = "post_merge"

    PRE_CLEANUP = "pre_cleanup"
    POST_CLEANUP = "post_cleanup"

    ON_ERROR = "on_error"
    ON_COMPLETE = "on_complete"

    PRE_PLANNING_COMMENT = "pre_planning_comment"
    POST_PLANNING_COMMENT = "post_planning_comment"
    PRE_UPDATE_CHECKLIST = "pre_update_checklist"
    POST_UPDATE_CHECKLIST = "post_update_checklist"


class FlowHookSpec:
    """Hook specifications for flow lifecycle events.

    Implementations use the @hookimpl decorator from modules/hooks.py.

    Example:

        from modules.hooks import FlowPhase, hookimpl

        class MyHooks:
            @hookimpl
            def on_flow_phase(self, phase, flow_id, state, result=None):
                if phase == FlowPhase.POST_COMMIT:
                    print(f"Commit made in flow {flow_id}")
    """

    @hookspec
    def on_flow_start(self, flow_id: str, state: object) -> None:
        """Called when a flow begins execution."""
        ...

    @hookspec
    def on_flow_phase(
        self,
        phase: FlowPhase,
        flow_id: str,
        state: object,
        result: object | None = None,
    ) -> None:
        """Called at each flow phase transition.

        Args:
            phase: Which phase is firing.
            flow_id: Unique flow identifier.
            state: The flow's state model (read-only reference).
            result: Return value of the phase method (if any).
        """
        ...

    @hookspec
    def on_flow_complete(self, flow_id: str, state: object) -> None:
        """Called when flow finishes successfully (after cleanup)."""
        ...

    @hookspec
    def on_flow_error(self, flow_id: str, state: object, error: Exception) -> bool | None:
        """Called on unhandled flow exception.

        Return True to suppress the exception and allow flow to continue.
        Return None or False to let the exception propagate.
        """
        ...

    @hookspec(firstresult=True)
    def should_skip_phase(self, phase: FlowPhase, flow_id: str, state: object) -> bool | None:
        """Allow modules to skip a phase.

        Return True to skip the phase. firstresult=True means
        first True response wins and remaining hooks are not called.
        """
        ...

    @hookspec
    def modify_state(self, phase: FlowPhase, flow_id: str, state: object) -> None:
        """Allow modules to mutate flow state between phases.

        State is a mutable Pydantic model. Changes persist to next phase.
        """
        ...


def get_plugin_manager() -> pluggy.PluginManager:
    """Create and configure a plugin manager with hook specs."""
    pm = pluggy.PluginManager(POLYCODE_NS)
    pm.add_hookspecs(FlowHookSpec)
    return pm
