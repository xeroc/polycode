"""Central registry for all resources (modules, flows, tasks)."""

import logging
from typing import TYPE_CHECKING, Any

import pluggy

if TYPE_CHECKING:
    from modules.context import ModuleContext

from modules.protocol import PolycodeModule

log = logging.getLogger(__name__)


class FlowRegistry:
    """Registry for flow definitions contributed by modules."""

    def __init__(self) -> None:
        self._flows: dict[str, Any] = {}

    def register(self, flow_def: Any) -> None:
        """Register a flow definition.

        Args:
            flow_def: Flow definition to register.

        Raises:
            ValueError: If flow name is empty or kickoff_func is not callable.
        """
        if not flow_def.name:
            raise ValueError("Flow name cannot be empty")
        if not callable(flow_def.kickoff_func):
            raise ValueError(f"Flow '{flow_def.name}' kickoff_func must be callable")

        if flow_def.name in self._flows:
            log.warning(f"⚠️ Flow '{flow_def.name}' already registered, overwriting")

        self._flows[flow_def.name] = flow_def
        log.info(f"📜 Registered flow: {flow_def.name}")

    def get_flow(self, name: str) -> Any | None:
        """Get a flow by name.

        Args:
            name: Flow identifier.

        Returns:
            match if found, None otherwise.
        """
        return self._flows.get(name)

    def get_flow_for_label(self, label: str) -> Any | None:
        """Find a flow that handles given label.

        Matches label against each flow's supported_labels (with prefix stripping).
        Returns highest priority match.

        Args:
            label: Full label string (e.g., "polycode:implement").

        Returns:
            match if found, None otherwise.
        """
        from project_manager.config import settings

        prefix = settings.FLOW_LABEL_PREFIX
        if not label.startswith(prefix):
            log.debug(f"Label '{label}' missing prefix '{prefix}'")
            return None

        stripped_label = label[len(prefix) :]
        matches: list[Any] = []

        for flow in self._flows.values():
            if stripped_label in flow.supported_labels:
                matches.append(flow)

        if not matches:
            log.debug(f"No flow found for label '{label}'")
            return None

        matches.sort(key=lambda f: f.priority, reverse=True)
        best_match = matches[0]
        log.info(f"🎯 Flow '{best_match.name}' matched label '{label}' (priority: {best_match.priority})")
        return best_match

    def list_flows(self) -> list[str]:
        """List all registered flow names."""
        return list(self._flows.keys())

    def collect_from_modules(self, modules: dict[str, Any]) -> int:
        """Collect flows from all modules.

        Called by load_all() after modules are loaded.

        Args:
            modules: Dict of module_name -> module class.

        Returns:
            Number of flows collected.
        """
        count = 0
        for name, module in modules.items():
            if hasattr(module, "get_flows"):
                try:
                    flows = module.get_flows()
                    for flow in flows:
                        self.register(flow)
                        count += 1
                except Exception as e:
                    log.error(f"🚨 Module '{name}' get_flows() failed: {e}")

        log.info(f"📜 Collected {count} flows from modules")
        return count


class TaskRegistry:
    """Registry for Celery tasks contributed by modules.

    Collects task definitions from modules during load_all() and
    provides registration with a Celery app.
    """

    def __init__(self) -> None:
        self._tasks: dict[str, dict[str, Any]] = {}

    @property
    def tasks(self) -> dict[str, dict[str, Any]]:
        """All registered task definitions."""
        return dict(self._tasks)

    def register(self, module_name: str, task_def: dict[str, Any]) -> None:
        """Register a single task from a module.

        Args:
            module_name: Name of the module providing the task.
            task_def: Task definition with 'name', 'func', and optional 'options'.

        Raises:
            ValueError: If task definition is invalid.
        """
        if "name" not in task_def:
            raise ValueError(f"Task from '{module_name}' missing 'name' field")
        if "func" not in task_def:
            raise ValueError(f"Task '{task_def.get('name')}' missing 'func' field")

        task_name = f"{module_name}.{task_def['name']}"
        if task_name in self._tasks:
            log.warning(f"⚠️ Task '{task_name}' already registered, overwriting")

        self._tasks[task_name] = {
            "func": task_def["func"],
            "options": task_def.get("options", {}),
            "module": module_name,
        }
        log.info(f"📝 Registered task: {task_name}")

    def collect_from_modules(self, modules: dict[str, Any]) -> int:
        """Collect tasks from all modules.

        Args:
            modules: Dict of module name -> module class from ModuleRegistry.

        Returns:
            Number of tasks collected.
        """
        count = 0
        for module_name, module in modules.items():
            try:
                task_defs = module.get_tasks()
                for task_def in task_defs:
                    self.register(module_name, task_def)
                    count += 1
            except Exception as e:
                log.error(f"🚨 Failed to collect tasks from '{module_name}': {e}")

        log.info(f"📦 Collected {count} tasks from {len(modules)} modules")
        return count

    def register_all(self, celery_app: Any) -> list[str]:
        """Register all collected tasks with a Celery app.

        Args:
            celery_app: Celery application instance.

        Returns:
            List of registered task names.
        """
        registered = []
        for task_name, task_info in self._tasks.items():
            try:
                func = task_info["func"]
                options = task_info["options"]

                decorator = celery_app.task(
                    name=task_name,
                    **options,
                )
                decorator(func)
                registered.append(task_name)
                log.info(f"✅ Registered Celery task: {task_name}")
            except Exception as e:
                log.error(f"🚨 Failed to register task '{task_name}': {e}")

        return registered

    def get_task_names(self) -> list[str]:
        """Get list of all registered task names."""
        return list(self._tasks.keys())


class ModuleRegistry:
    """Central registry for modules, flows, and tasks."""

    def __init__(self) -> None:
        self._modules: dict[str, PolycodeModule] = {}
        self._pm = pluggy.PluginManager("polycode")

        self._flow_registry = FlowRegistry()
        self._task_registry = TaskRegistry()

    @property
    def pm(self) -> pluggy.PluginManager:
        """The shared plugin manager."""
        return self._pm

    @property
    def modules(self) -> dict[str, PolycodeModule]:
        """All registered modules."""
        return dict(self._modules)

    @property
    def flow_registry(self) -> FlowRegistry:
        """Flow registry instance."""
        return self._flow_registry

    @property
    def task_registry(self) -> TaskRegistry:
        """Task registry instance."""
        return self._task_registry

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

    def register_builtin(self, module) -> None:
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
        4. Collect flows from all modules.
        5. Collect Celery tasks from all modules.

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

        self._flow_registry.collect_from_modules(self._modules)
        self._task_registry.collect_from_modules(self._modules)

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
