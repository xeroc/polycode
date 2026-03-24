"""Celery worker initialization and task registration."""

import logging

from tasks import app, tasks

assert app
assert tasks

log = logging.getLogger(__name__)


@app.task()
def hello():
    return "hello world"


def register_module_tasks() -> list[str]:
    """Register tasks from all loaded modules.

    Modules can define get_tasks() to contribute async tasks.

    Returns:
        List of registered task names.
    """
    from modules import get_task_registry

    registry = get_task_registry()
    return registry.register_all(app)


app.autodiscover_tasks()  # discovers tasks.py in all INSTALLED_APPS
