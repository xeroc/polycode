"""Specify flow module definition."""

from typing import TYPE_CHECKING

from ..protocol import FlowDef

if TYPE_CHECKING:
    import pluggy

    from modules.context import ModuleContext


class SpecifyModule:
    """Module providing the Ralph flow."""

    name = "specify"
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
        from flows.specify.flow import kickoff

        return [
            FlowDef(
                name="specify",
                kickoff_func=kickoff,
                description="Specify - generate assisted specs",
                supported_labels=["specify"],
                priority=1,
            )
        ]
