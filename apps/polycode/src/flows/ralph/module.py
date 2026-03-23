"""Ralph flow module for the polycode system."""

from typing import TYPE_CHECKING

from ..protocol import FlowDef

if TYPE_CHECKING:
    import pluggy

    from modules.context import ModuleContext


class RalphModule:
    """Module providing the Ralph flow."""

    name = "ralph"
    version = "1.0.0"
    dependencies: list[str] = []

    @classmethod
    def on_load(cls, context: "ModuleContext") -> None:
        pass

    @classmethod
    def register_hooks(cls, pm: "pluggy.PluginManager") -> None:
        pass

    @classmethod
    def get_flows(cls) -> list[FlowDef]:
        """Return flow definitions provided by this module."""
        from flows.ralph.flow import kickoff

        return [
            FlowDef(
                name="ralph",
                kickoff_func=kickoff,
                description="Ralph Loop - automated software development flow",
                supported_labels=["implement"],
                priority=1,
            )
        ]
