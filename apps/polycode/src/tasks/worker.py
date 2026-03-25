"""Celery worker initialization and task registration."""

import logging

from bootstrap import get_module_registry
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
    registry = get_module_registry().task_registry
    return registry.register_all(app)


app.autodiscover_tasks()  # discovers tasks.py in all INSTALLED_APPS
