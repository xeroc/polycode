"""Celery configuration for feature development tasks."""

import os

from celery import Celery

REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
REDIS_DB = int(os.environ.get("REDIS_DB", 0))

broker_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
RESULT_BACKEND = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"

app = Celery("feature_dev")
app.conf.update(
    broker_url=broker_url,
    result_backend=RESULT_BACKEND,
    # task_serializer="json",
    # accept_content=["json"],
    # result_serializer="json",
    # timezone="UTC",
    # enable_utc=True,
    # task_track_started=True,
    # task_time_limit=7200,
    # task_soft_time_limit=6600,
    # task_acks_late=True,
    # worker_prefetch_multiplier=1,
    # broker_connection_retry_on_startup=True,
    # broker_connection_retry=True,
    # broker_connection_max_retries=5,
    # result_expires=86400,
    # task_routes={
    #     "celery_tasks.tasks.kickoff_feature_dev_task": {
    #         "queue": "feature_dev",
    #         "routing_key": "feature_dev",
    #     },
    #     "celery_tasks.tasks.implement_story_task": {
    #         "queue": "feature_dev",
    #         "routing_key": "feature_dev",
    #     },
    #     "celery_tasks.tasks.test_story_task": {
    #         "queue": "feature_dev",
    #         "routing_key": "feature_dev",
    #     },
    #     "celery_tasks.tasks.process_github_webhook_task": {
    #         "queue": "webhooks",
    #         "routing_key": "webhooks",
    #     },
    #     "celery_tasks.tasks.update_status_task": {
    #         "queue": "monitoring",
    #         "routing_key": "monitoring",
    #     },
    #     "celery_tasks.tasks.flow_heartbeat_task": {
    #         "queue": "monitoring",
    #         "routing_key": "monitoring",
    #     },
    #     "celery_tasks.tasks.cleanup_completed_tasks": {
    #         "queue": "cleanup",
    #         "routing_key": "cleanup",
    #     },
    # },
    # task_default_queue="default",
    # task_queues={
    #     "feature_dev": {
    #         "exchange": "feature_dev",
    #         "routing_key": "feature_dev",
    #     },
    #     "webhooks": {
    #         "exchange": "webhooks",
    #         "routing_key": "webhooks",
    #     },
    #     "monitoring": {
    #         "exchange": "monitoring",
    #         "routing_key": "monitoring",
    #     },
    #     "cleanup": {
    #         "exchange": "cleanup",
    #         "routing_key": "cleanup",
    #     },
    # },
)
