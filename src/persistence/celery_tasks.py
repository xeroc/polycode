"""Celery task tracking in PostgreSQL."""

from datetime import datetime, timedelta, timezone

from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import String, DateTime, Integer, Text

from .postgres import Base


class CeleryTask(Base):
    """Celery task tracking model.

    Tracks all Celery tasks for monitoring and debugging purposes.
    """

    __tablename__ = "celery_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    flow_id: Mapped[str] = mapped_column(String(255), nullable=False)
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    issue_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    __table_args__ = (
        Index("idx_celery_tasks_flow_id", "flow_id"),
        Index("idx_celery_tasks_status", "status"),
        Index("idx_celery_tasks_task_type", "task_type"),
    )


class CeleryTaskTracker:
    """Track Celery tasks in PostgreSQL."""

    def __init__(self, session_factory):
        """Initialize task tracker.

        Args:
            session_factory: SQLAlchemy session factory
        """
        self.Session = session_factory

    def create_task(
        self,
        task_id: str,
        flow_id: str,
        task_type: str,
        issue_number: int | None = None,
    ) -> None:
        """Create a new task record.

        Args:
            task_id: Celery task ID
            flow_id: Flow ID this task belongs to
            task_type: Type of task (e.g., 'implement_story', 'test_story')
            issue_number: Optional GitHub issue number
        """
        with self.Session() as session:
            task = CeleryTask(
                task_id=task_id,
                flow_id=flow_id,
                task_type=task_type,
                status="pending",
                created_at=datetime.now(timezone.utc),
                issue_number=issue_number,
            )
            session.add(task)
            session.commit()

    def update_task_started(self, task_id: str) -> None:
        """Mark task as started.

        Args:
            task_id: Celery task ID
        """
        with self.Session() as session:
            task = (
                session.query(CeleryTask).filter(CeleryTask.task_id == task_id).first()
            )
            if task:
                task.status = "running"
                task.started_at = datetime.now(timezone.utc)
                session.commit()

    def update_task_completed(self, task_id: str, result: str | None = None) -> None:
        """Mark task as completed.

        Args:
            task_id: Celery task ID
            result: Optional result data
        """
        with self.Session() as session:
            task = (
                session.query(CeleryTask).filter(CeleryTask.task_id == task_id).first()
            )
            if task:
                task.status = "completed"
                task.completed_at = datetime.now(timezone.utc)
                task.result = result
                session.commit()

    def update_task_failed(self, task_id: str, error_message: str) -> None:
        """Mark task as failed.

        Args:
            task_id: Celery task ID
            error_message: Error message
        """
        with self.Session() as session:
            task = (
                session.query(CeleryTask).filter(CeleryTask.task_id == task_id).first()
            )
            if task:
                task.status = "failed"
                task.completed_at = datetime.now(timezone.utc)
                task.error_message = error_message
                session.commit()

    def increment_retry(self, task_id: str) -> None:
        """Increment retry count.

        Args:
            task_id: Celery task ID
        """
        with self.Session() as session:
            task = (
                session.query(CeleryTask).filter(CeleryTask.task_id == task_id).first()
            )
            if task:
                task.retry_count += 1
                session.commit()

    def get_task(self, task_id: str) -> CeleryTask | None:
        """Get task by ID.

        Args:
            task_id: Celery task ID

        Returns:
            CeleryTask if found, None otherwise
        """
        with self.Session() as session:
            return (
                session.query(CeleryTask).filter(CeleryTask.task_id == task_id).first()
            )

    def get_flow_tasks(self, flow_id: str) -> list[CeleryTask]:
        """Get all tasks for a flow.

        Args:
            flow_id: Flow ID

        Returns:
            List of CeleryTask objects
        """
        with self.Session() as session:
            return (
                session.query(CeleryTask)
                .filter(CeleryTask.flow_id == flow_id)
                .order_by(CeleryTask.created_at)
                .all()
            )

    def cleanup_completed_tasks(self, days_old: int = 7) -> int:
        """Delete completed/failed tasks older than specified days.

        Args:
            days_old: Number of days to keep completed tasks

        Returns:
            Number of tasks deleted
        """
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_old)

        with self.Session() as session:
            deleted = (
                session.query(CeleryTask)
                .filter(
                    CeleryTask.status.in_(["completed", "failed"]),
                    CeleryTask.completed_at < cutoff_date,
                )
                .delete()
            )
            session.commit()
            return deleted
