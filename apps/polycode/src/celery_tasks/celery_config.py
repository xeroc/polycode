"""Celery configuration for feature development tasks."""

from celery import Celery
from pydantic_settings import BaseSettings, SettingsConfigDict


class CelerySettings(BaseSettings):
    # Celery Configuration
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    DATABASE_URL: str

    GITHUB_PROJECT_STATUS_MAPPING: dict[str, str] = dict(
        todo="Backlog",
        ready="Ready",
        in_progress="In progress",
        reviewing="In review",
        done="Done",
    )

    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int = 0

    model_config = SettingsConfigDict(extra="ignore", env_file=".env", case_sensitive=True)


settings = CelerySettings()  # pyright:ignore # ty:ignore


broker_url = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
result_backend = f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"


app = Celery(__name__)
app.conf.update(
    broker_url=broker_url,
    result_backend=result_backend,
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
    #     "celery_tasks.tasks.kickoff_task": {
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
