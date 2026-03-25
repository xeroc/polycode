"""Ralph flow module for the polycode system."""

from typing import TYPE_CHECKING, Any, ClassVar

from ..protocol import FlowDef

if TYPE_CHECKING:
    import pluggy

    from modules.context import ModuleContext


class RalphModule:
    """Module providing the Ralph flow."""

    name: ClassVar[str] = "ralph"
    version: ClassVar[str] = "1.0.0"
    dependencies: ClassVar[list[str]] = []

    @classmethod
    def on_load(cls, context: "ModuleContext") -> None:
        pass

    @classmethod
    def register_hooks(cls, hook_manager: "pluggy.PluginManager") -> None:
        pass

    @classmethod
    def get_models(cls) -> list[type]:
        return []

    @classmethod
    def get_tasks(cls) -> list[dict[str, Any]]:
        return []

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
