"""Protocol for polycode modules."""

from typing import TYPE_CHECKING, ClassVar, Protocol, runtime_checkable

if TYPE_CHECKING:
    from modules.context import ModuleContext

if TYPE_CHECKING:
    import pluggy


@runtime_checkable
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

    name: ClassVar[str]
    version: ClassVar[str] = "0.0.0"
    dependencies: ClassVar[list[str]] = []

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
