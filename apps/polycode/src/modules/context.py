"""Context object passed to modules during initialization."""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy import Engine

if TYPE_CHECKING:
    import pluggy


@dataclass
class ModuleContext:
    """Shared context for module initialization.

    Passed to module.on_load() during bootstrap.
    """

    db_engine: "Engine"
    db_url: str
    hook_manager: "pluggy.PluginManager"
    config: dict[str, Any] = field(default_factory=dict)

    def get_module_config(self, module_name: str) -> dict[str, Any]:
        """Get config dict for a specific module.

        Config is loaded from environment or config file.
        Module-specific config lives under config[module_name].
        """
        return self.config.get(module_name, {})
