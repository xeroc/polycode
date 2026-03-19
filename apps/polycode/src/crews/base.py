"""PolycodeCrewMixin base class with automatic hook emission.

All Polycode crews should extend this base class to automatically emit
CREW_FINISHED events via the @after_kickoff decorator.
"""

import logging
from typing import TYPE_CHECKING

import pluggy
from crewai.project import CrewBase, after_kickoff

if TYPE_CHECKING:
    from crewai import CrewOutput

logger = logging.getLogger(__name__)

# Just a rename
PolyCodeBase = CrewBase


class PolycodeCrewMixin:
    """Base class for all Polycode crews.

    Automatically emits CREW_FINISHED event after crew execution completes.
    Subclasses must define a `crew_label` class attribute to identify the crew
    in hook events (e.g., "plan", "implement", "review").

    Example:

        @CrewBase
        class PlanCrew(PolycodeCrewMixin):
            crew_label = "plan"

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

    The @after_kickoff hook will automatically emit:
        FlowEvent.CREW_FINISHED, label="plan", result=crew_output
    """

    crew_label: str = "unknown"
    _pm: pluggy.PluginManager | None = None

    @classmethod
    def configure_hooks(cls, pm: pluggy.PluginManager) -> None:
        """Set the plugin manager for all crew instances."""
        cls._pm = pm

    @after_kickoff
    def emit_crew_finished(self, output: "CrewOutput") -> "CrewOutput":
        """Emit CREW_FINISHED event after crew execution.

        This hook is automatically called by CrewAI after the crew completes.
        """
        if not self._pm:
            logger.debug(f"No plugin manager configured for {self.crew_label} crew")
            return output

        try:
            from modules.hooks import FlowEvent

            self._pm.hook.on_flow_event(
                event=FlowEvent.CREW_FINISHED,
                flow_id="",  # Flow will set this via state
                state={},  # Flow will provide state
                result=output,
                label=self.crew_label,
            )
            logger.info(f"✅ {self.crew_label.capitalize()} crew finished")
        except Exception as e:
            logger.warning(f"⚠️ Hook error in {self.crew_label} crew: {e}")

        return output
