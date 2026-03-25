"""Specify flow module definition."""

from typing import TYPE_CHECKING, Any, ClassVar

from ..protocol import FlowDef

if TYPE_CHECKING:
    import pluggy

    from modules.context import ModuleContext


class SpecifyModule:
    """Module providing the Ralph flow."""

    name: ClassVar[str] = "specify"
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
