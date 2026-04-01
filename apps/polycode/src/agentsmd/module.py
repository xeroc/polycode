"""AgentsMD built-in module for the Polycode plugin system."""

from typing import Any


class AgentsMDPolycodeModule:
    """AgentsMD module: discovers and injects AGENTS.md content."""

    name = "agentsmd"
    version = "0.1.0"
    dependencies: list[str] = []

    @classmethod
    def on_load(cls, context: Any) -> None:
        pass

    @classmethod
    def register_hooks(cls, hook_manager: Any) -> None:
        pass

    @classmethod
    def get_context_injectors(cls) -> list[Any]:
        from .injector import AgentsMDInjector

        return [AgentsMDInjector()]
