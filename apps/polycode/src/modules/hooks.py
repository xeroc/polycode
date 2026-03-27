"""Flow orchestration event specifications.

Uses pluggy (already a dependency of crewai via pytest) for hook management.

Events focus on flow orchestration (git, PRs, cleanup) - NOT crew-level lifecycle.
CrewAI already provides @before_kickoff and @after_kickoff decorators for crews.

Modules register hook implementations via @hookimpl decorator.
"""

from enum import StrEnum
from typing import TYPE_CHECKING, Any

import pluggy

if TYPE_CHECKING:
    pass

POLYCODE_NS = "polycode"

hookspec = pluggy.HookspecMarker(POLYCODE_NS)
hookimpl = pluggy.HookimplMarker(POLYCODE_NS)


class FlowEvent(StrEnum):
    """Flow lifecycle events.

    Simplified event-based hook system. Plugins filter by event + label.

    Labels provide context:
    - CREW_FINISHED: "plan", "implement", "review"
    - STORY_COMPLETED: story.id or story.title
    - FLOW_STARTED/FINISHED: flow name (e.g., "ralph")

    Crew-level lifecycle (@before_kickoff, @after_kickoff) is handled by
    PolycodeCrewMixin base class which emits CREW_FINISHED events.
    """

    SETUP = "SETUP"
    FLOW_STARTED = "flow_started"
    FLOW_FINISHED = "flow_finished"
    FLOW_ERROR = "flow_error"

    CREW_FINISHED = "crew_finished"

    STORIES_PLANNED = "stories_planned"
    STORY_COMPLETED = "story_completed"

    COMMENT = "comment"
    ADD_LABEL = "add_label"

    CLEANUP = "cleanup"


class FlowHookSpec:
    """Hook specifications for flow lifecycle events.

    Implementations use the @hookimpl decorator from modules/hooks.py.

    Example:

        from modules.hooks import FlowEvent, hookimpl

        class MyHooks:
            @hookimpl
            def on_flow_event(self, event, flow_id, state, result=None, label=""):
                if event == FlowEvent.CREW_FINISHED and label == "plan":
                    print(f"Planning crew finished in flow {flow_id}")

                if event == FlowEvent.STORY_COMPLETED:
                    # Commit and push changes
                    self.git_ops.commit_and_push(state, result)

                if event == FlowEvent.FLOW_FINISHED:
                    # Create PR, merge, cleanup
                    self.finalize_flow(flow_id, state)
    """

    @hookspec
    def on_flow_event(
        self,
        event: FlowEvent,
        flow_id: str,
        state: Any,
        result: Any,
        label: str,
    ) -> None:
        """Called at each flow lifecycle event.

        Args:
            event: Which event is firing (FLOW_STARTED, CREW_FINISHED, etc.).
            flow_id: Unique flow identifier.
            state: The flow's state model (read-only reference).
            result: Event-specific result (e.g., Story object, crew output).
            label: Context label (e.g., "plan", "implement", "ralph").
        """
        ...


def get_plugin_manager() -> pluggy.PluginManager:
    """Create and configure a plugin manager with hook specs."""
    pm = pluggy.PluginManager(POLYCODE_NS)
    pm.add_hookspecs(FlowHookSpec)
    return pm
