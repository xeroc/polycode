"""Celery application for feature development tasks."""

import time
import uuid

from celery import Celery, Task
from celery.utils.log import get_task_logger

log = get_task_logger(__name__)


class BaseTask(Task):
    """Base task class with retry and error handling."""

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        log.error(
            f"Task {self.name}[{task_id}] failed: {exc}",
            exc_info=True,
        )
        super().on_failure(exc, task_id, args, kwargs, einfo)

    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success."""
        log.info(f"Task {self.name}[{task_id}] completed successfully")
        super().on_success(retval, task_id, args, kwargs)

    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Handle task retry."""
        log.warning(f"Task {self.name}[{task_id}] retrying: {exc}")
        super().on_retry(exc, task_id, args, kwargs, einfo)


def get_flow_id() -> str:
    """Generate a unique flow ID."""
    return f"flow_{int(time.time())}_{str(uuid.uuid4())[:8]}"


def calculate_timeout(retry_count: int) -> int:
    """Calculate exponential backoff timeout."""
    base_delay = 60
    max_delay = 3600
    delay = min(base_delay * (2**retry_count), max_delay)
    return delay


app = Celery(__name__, task_cls="celery_tasks.BaseTask")
app.config_from_object("celery_tasks.celery_config")


@app.task()
def base():
    return "base"


@app.task()
def hello():
    log.info("hello")
    return "hello"
