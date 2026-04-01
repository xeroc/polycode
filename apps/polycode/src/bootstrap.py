"""Application bootstrap — single entry point for initialization.

Call bootstrap() once at application startup (FastAPI lifespan, CLI, etc.).
After bootstrap, modules are loaded and hooks are active.
"""

import logging
from typing import Any

from flows.ralph.module import RalphModule
from flows.specify.module import SpecifyModule
from modules.context import ModuleContext
from modules.registry import ModuleRegistry
from persistence.postgres import DATABASE_URL, engine

log = logging.getLogger(__name__)

_module_registry: ModuleRegistry | None = None


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

    global _module_registry
    module_registry = ModuleRegistry()
    _module_registry = module_registry
    module_registry.discover()

    from gitcore import GitcoreModule
    from project_manager import ProjectManagerModule

    module_registry.register_builtin(RalphModule)  # type: ignore[arg-type]
    module_registry.register_builtin(SpecifyModule)  # type: ignore[arg-type]
    module_registry.register_builtin(ProjectManagerModule)  # type: ignore[arg-type]
    # git core last, so it gets called first! pull request require the branch is pushed!
    module_registry.register_builtin(GitcoreModule)  # type: ignore[arg-type]

    context = ModuleContext(
        db_engine=engine,
        db_url=DATABASE_URL,
        hook_manager=module_registry.pm,
        config=cfg.get("modules", {}),
    )
    # Collect all models from modules and create tables
    all_models: list[type] = []
    for module_name, module in module_registry.modules.items():
        if hasattr(module, "get_models"):
            try:
                models = module.get_models()
                all_models.extend(models)
            except Exception as e:
                log.error(f"🚨 Failed to get models from '{module_name}': {e}")

    # Create all tables in the database
    if all_models:
        from persistence.postgres import Base

        Base.metadata.create_all(engine)
        log.info(f"🗄 Created {len(all_models)} tables from {len(module_registry.modules)} modules")

    module_registry.load_all(context)

    from agentsmd import AgentsMDPolycodeModule

    module_registry.register_builtin(AgentsMDPolycodeModule)  # type: ignore[arg-type]
    module_registry.context_registry.collect_from_modules(module_registry.modules)

    from crews.base import PolycodeCrewMixin
    from crews.review_crew.postmortem import PostmortemHooks
    from flows.base import FlowIssueManagement

    FlowIssueManagement.use_plugin_manager(module_registry.pm)
    FlowIssueManagement.use_context_registry(module_registry.context_registry)
    PolycodeCrewMixin.use_plugin_manager(module_registry.pm)

    module_registry.pm.register(PostmortemHooks(), name="postmortem")
    log.info("📋 Registered postmortem hooks")

    module_count = len(module_registry.modules)
    log.info(f"🚀 Bootstrap complete: {module_count} modules")

    return context


def get_module_registry() -> ModuleRegistry:
    """Get the module registry instance.

    Calls bootstrap() if not already initialized.

    Returns:
        The global ModuleRegistry instance.
    """
    global _module_registry
    if _module_registry is None:
        bootstrap()
    assert _module_registry is not None
    return _module_registry
