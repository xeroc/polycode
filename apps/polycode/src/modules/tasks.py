"""Celery task registry for module-based task registration."""

import logging
from typing import Any

log = logging.getLogger(__name__)


class TaskRegistry:
    """Registry for Celery tasks contributed by modules.

    Collects task definitions from modules during load_all() and
    provides registration with a Celery app.

    Usage:
        registry = TaskRegistry()
        registry.collect_from_modules(module_registry)
        registry.register_all(celery_app)
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


_task_registry: TaskRegistry | None = None


def get_task_registry() -> TaskRegistry:
    """Get the global task registry singleton."""
    global _task_registry
    if _task_registry is None:
        _task_registry = TaskRegistry()
    return _task_registry


def reset_task_registry() -> None:
    """Reset the global task registry (for testing)."""
    global _task_registry
    _task_registry = None
