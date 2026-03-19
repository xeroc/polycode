"""Module discovery and lifecycle management."""

import logging
from typing import TYPE_CHECKING

import pluggy

if TYPE_CHECKING:
    from modules.context import ModuleContext

from modules.hooks import get_plugin_manager
from modules.protocol import PolycodeModule
from modules.tasks import get_task_registry

log = logging.getLogger(__name__)


class ModuleRegistry:
    """Discovers external modules via entry points and manages loading."""

    def __init__(self) -> None:
        self._modules: dict[str, PolycodeModule] = {}
        self._pm = get_plugin_manager()

    @property
    def pm(self) -> pluggy.PluginManager:
        """The shared plugin manager."""
        return self._pm

    @property
    def modules(self) -> dict[str, PolycodeModule]:
        """All registered modules."""
        return dict(self._modules)

    def discover(self) -> None:
        """Scan entry points for external polycode modules.

        Looks for entry_points under group "polycode.modules".
        Each entry point should resolve to a class or object
        satisfying PolycodeModule protocol.
        """
        import importlib.metadata

        group = "polycode.modules"
        try:
            eps = importlib.metadata.entry_points().select(group=group)
        except (AttributeError, TypeError):
            eps = []

        for ep in eps:
            try:
                module_cls = ep.load()
                if not hasattr(module_cls, "name"):
                    log.warning(f"⚠️ Entry point '{ep.name}' missing 'name' attribute, skipping")
                    continue
                self._modules[ep.name] = module_cls
                log.info(f"📦 Discovered external module: {ep.name} (v{getattr(module_cls, 'version', '?')})")
            except Exception as e:
                log.error(f"🚨 Failed to load module '{ep.name}': {e}")

    def register_builtin(self, module: PolycodeModule) -> None:
        """Register a built-in module explicitly.

        Args:
            module: A class or object satisfying PolycodeModule protocol.
        """
        name = module.name
        if name in self._modules:
            log.warning(f"⚠️ Module '{name}' already registered, overwriting")
        self._modules[name] = module
        log.info(f"📦 Registered built-in module: {name}")

    def load_all(self, context: "ModuleContext") -> None:
        """Load all modules in dependency order.

        1. Topological sort based on dependencies.
        2. Call on_load() for each module.
        3. Call register_hooks() for each module.
        4. Collect Celery tasks from all modules.

        Raises:
            RuntimeError: If circular dependency detected.
        """
        sorted_names = self._topological_sort()

        for name in sorted_names:
            module = self._modules[name]
            log.info(f"🔧 Loading module: {name}")

            try:
                module.on_load(context)
            except Exception as e:
                log.error(f"🚨 Module '{name}' on_load() failed: {e}")
                raise

            try:
                module.register_hooks(self._pm)
            except Exception as e:
                log.error(f"🚨 Module '{name}' register_hooks() failed: {e}")
                raise

            log.info(f"✅ Module loaded: {name}")

        self._collect_celery_tasks()

    def _collect_celery_tasks(self) -> int:
        """Collect Celery tasks from all loaded modules.

        Returns:
            Number of tasks collected.
        """
        task_registry = get_task_registry()
        count = task_registry.collect_from_modules(self._modules)
        return count

    def _topological_sort(self) -> list[str]:
        """Sort modules by dependencies using Kahn's algorithm.

        Returns:
            List of module names in dependency order.

        Raises:
            RuntimeError: If circular dependency detected.
        """
        in_degree: dict[str, int] = {name: 0 for name in self._modules}
        dependents: dict[str, list[str]] = {name: [] for name in self._modules}

        for name, module in self._modules.items():
            for dep in getattr(module, "dependencies", []):
                if dep not in self._modules:
                    log.warning(f"⚠️ Module '{name}' depends on '{dep}' which is not registered")
                    continue
                dependents[dep].append(name)
                in_degree[name] += 1

        queue = [name for name, deg in in_degree.items() if deg == 0]
        result: list[str] = []

        while queue:
            node = queue.pop(0)
            result.append(node)
            for dependent in dependents[node]:
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        if len(result) != len(self._modules):
            remaining = set(self._modules) - set(result)
            raise RuntimeError(f"Circular dependency detected among modules: {remaining}")

        return result
