"""Protocol for polycode modules."""

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from flows.protocol import FlowDef
    from modules.context import ModuleContext

if TYPE_CHECKING:
    import pluggy


class PolycodeModule(Protocol):
    """Protocol that all modules (built-in and external) must satisfy.

    A module is a class or object with:

    - name (str): Unique module identifier.
    - version (str): Semantic version.
    - dependencies (list[str]): Names of modules that must load first.

    Methods are classmethods so modules can be defined as classes
    without instantiation.

    Built-in modules are registered explicitly in bootstrap().
    External modules are discovered via entry_points["polycode.modules"].
    """

    name: str
    version: str
    dependencies: list[str]

    @classmethod
    def on_load(cls, context: "ModuleContext") -> None:
        """Called after all models are registered and tables created.

        Initialize module resources (DB connections, caches, etc.).
        """
        ...

    @classmethod
    def register_hooks(cls, hook_manager: "pluggy.PluginManager") -> None:
        """Register hook implementations.

        Called after on_load(). Modules that don't use hooks can no-op.
        """
        ...

    @classmethod
    def get_models(cls) -> list[type]:
        """Return ORM model classes for this module.

        Optional — models are auto-registered via RegisteredBase.
        This method is for explicit listing when needed (docs, introspection).
        """
        return []

    @classmethod
    def get_tasks(cls) -> list[dict[str, Any]]:
        """Return Celery task definitions from this module.

        Each dict should contain:
            - name: str - Task name (will be prefixed with module name)
            - func: Callable - Task function
            - options: dict (optional) - Task options (bind, max_retries, etc.)

        Returns:
            List of task definition dicts.

        Example:
            return [
                {"name": "process_data", "func": process_data_task, "options": {"bind": True}},
                {"name": "cleanup", "func": cleanup_task},
            ]
        """
        return []

    @classmethod
    def get_flows(cls) -> list["FlowDef"]:
        """Return flow definitions provided by this module.

        Each flow can declare which labels it handles via supported_labels.
        Labels are matched against FLOW_LABEL_PREFIX (default: "polycode:").

        Returns:
            List of FlowDef instances. Empty list if module provides no flows.
        """
        if TYPE_CHECKING:
            pass
        return []
