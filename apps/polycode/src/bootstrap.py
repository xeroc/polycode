"""Application bootstrap — single entry point for initialization.

Call bootstrap() once at application startup (FastAPI lifespan, CLI, etc.).
After bootstrap, modules are loaded and hooks are active.
"""

import logging
import os
from typing import Any

import pluggy
from sqlalchemy import create_engine

from modules.context import ModuleContext
from modules.registry import ModuleRegistry
from persistence.registry import ModelRegistry

log = logging.getLogger(__name__)


def bootstrap(config: dict[str, Any] | None = None) -> ModuleContext:
    """Initialize full polycode runtime.

    Steps:
        1. Create SQLAlchemy engine
        2. Import all model modules (triggers __init_subclass__ registration)
        3. Discover external modules via entry points
        4. Register built-in modules
        5. Create all database tables
        6. Load all modules (on_load + register_hooks)

    Args:
        config: Optional config dict. Keys:
            - db_url: str (default: DATABASE_URL env var)
            - modules: dict of module_name -> module_config dicts

    Returns:
        ModuleContext with engine, hook manager, and config.

    Example:

        from bootstrap import bootstrap
        context = bootstrap()
        # Now all modules are loaded, hooks are active, tables exist
    """
    cfg = config or {}

    db_url = cfg.get("db_url") or os.getenv(
        "DATABASE_URL",
        "postgresql://user:password@localhost:5432/polycode",
    )
    engine = create_engine(db_url)

    import persistence.postgres  # noqa: F401

    module_registry = ModuleRegistry()
    module_registry.discover()

    from gitcore import GitcoreModule
    from project_manager import ProjectManagerModule

    module_registry.register_builtin(GitcoreModule)  # type: ignore[arg-type]
    module_registry.register_builtin(ProjectManagerModule)  # type: ignore[arg-type]

    ModelRegistry.create_all(engine)

    context = ModuleContext(
        db_engine=engine,
        db_url=db_url,
        hook_manager=module_registry.pm,
        config=cfg.get("modules", {}),
    )
    module_registry.load_all(context)

    module_count = len(module_registry.modules)
    model_count = len(ModelRegistry.all_models())
    log.info(f"🚀 Bootstrap complete: {module_count} modules, {model_count} tables")

    return context


def init_plugins() -> pluggy.PluginManager:
    """Lightweight plugin initialization for CLI/Celery entry points.

    Registers the channels module and triggers channel self-registration
    by importing channel implementations.

    This is a minimal bootstrap that doesn't require database setup.
    Use bootstrap() for full application initialization.

    Returns:
        Configured plugin manager with channels hooks registered.

    Example:

        from bootstrap import init_plugins
        pm = init_plugins()
        # Now channel notifications will work during flow execution
    """
    from modules.hooks import get_plugin_manager

    pm = get_plugin_manager()

    # Register channels module (this registers ChannelHooks)
    from channels import ChannelsPolycodeModule

    ChannelsPolycodeModule.register_hooks(pm)

    # Import channel implementations to trigger self-registration
    import channels.github  # noqa: F401
    import channels.redis  # noqa: F401

    log.info("🔌 Plugin system initialized (channels active)")

    return pm
