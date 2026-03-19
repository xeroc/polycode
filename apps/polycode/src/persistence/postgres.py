"""PostgreSQL-based flow state persistence using SQLAlchemy with JSONB."""

from persistence.config import settings

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from crewai.flow.async_feedback.types import PendingFeedbackContext
from crewai.flow.persistence import FlowPersistence, SQLiteFlowPersistence
from pydantic import BaseModel
from sqlalchemy import Index, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    sessionmaker,
)
from sqlalchemy.sql.expression import text
from sqlalchemy.types import JSON, DateTime, Integer, String, TypeDecorator

DATABASE_URL = settings.DATABASE_URL

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""


class JSONType(TypeDecorator):
    """Platform-independent JSON type. Uses JSONB for PostgreSQL, JSON for others."""

    impl = JSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(JSONB())
        return dialect.type_descriptor(JSON())


class Payments(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    issue_number: Mapped[int] = mapped_column()
    payment_id: Mapped[str] = mapped_column()
    amount: Mapped[int] = mapped_column()
    currency: Mapped[str] = mapped_column()
    payment_method: Mapped[str] = mapped_column()
    status: Mapped[str] = mapped_column()
    created_at: Mapped[datetime | None] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))
    verified_at: Mapped[datetime | None] = mapped_column(default=None)


class Requests(Base):
    """Flow state table model."""

    __tablename__ = "requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    issue_number: Mapped[int] = mapped_column(Integer, nullable=False)
    request_text: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)
    commit: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


def update_request_status(
    session: sessionmaker,
    issue_number: int,
    status: str,
    commit: Optional[str] = None,
) -> bool:
    """Update the status of a request by issue_number.

    Args:
        session: SQLAlchemy session factory
        issue_number: The issue_number to update
        status: The new status value

    Returns:
        True if a row was updated, False otherwise
    """
    with session() as sess:
        result = sess.query(Requests).filter_by(issue_number=issue_number).update({"status": status, "commit": commit})
        sess.commit()
        return result > 0


def ensure_request_exists(
    session: sessionmaker,
    issue_number: int,
    body: str,
    status: str = "pending",
) -> bool:
    """Ensure a request exists for the given issue_number, inserting if needed.

    Args:
        session: SQLAlchemy session factory
        issue_number: The issue_number to check/insert
        body: The issue body text
        status: The status for new requests (default: "pending")

    Returns:
        True if a new request was inserted, False if it already existed
    """
    with session() as sess:
        existing = sess.query(Requests).filter_by(issue_number=issue_number).first()
        if existing:
            return False

        new_payment = Payments(
            issue_number=issue_number,
            status="manual",
            payment_id="none",
            amount=0,
            currency="USD",
            payment_method="none",
        )
        new_request = Requests(issue_number=issue_number, request_text=body, status=status)
        sess.add(new_payment)
        sess.commit()
        sess.add(new_request)
        sess.commit()
        return True


class FlowState(Base):
    """Flow state table model."""

    __tablename__ = "flow_states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    flow_uuid: Mapped[str] = mapped_column(String(255), nullable=False)
    method_name: Mapped[str] = mapped_column(String(255), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    state_json: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)

    __table_args__ = (Index("idx_flow_states_uuid", "flow_uuid"),)


class PendingFeedback(Base):
    """Pending feedback table model for async HITL."""

    __tablename__ = "pending_feedback"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    flow_uuid: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    context_json: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    state_json: Mapped[dict[str, Any]] = mapped_column(JSONType, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("idx_pending_feedback_uuid", "flow_uuid"),)


class PostgresFlowPersistence(FlowPersistence):
    """PostgreSQL-based implementation of flow state persistence.

    This class provides production-grade persistence using PostgreSQL with SQLAlchemy
    and JSONB for efficient querying of flow states.

    Example:
        ```python
        persistence = PostgresFlowPersistence(
            connection_string="postgresql://user:pass@localhost/db"
        )

        # Start a flow with async feedback
        try:
            flow = MyFlow(persistence=persistence)
            result = flow.kickoff()
        except HumanFeedbackPending as e:
            # Flow is paused, state is already persisted
            print(f"Waiting for feedback: {e.context.flow_id}")

        # Later, resume with feedback
        flow = MyFlow.from_pending("abc-123", persistence)
        result = flow.resume("looks good!")
        ```
    """

    def __init__(self, connection_string: str) -> None:
        """Initialize PostgreSQL persistence.

        Args:
            connection_string: PostgreSQL connection string.
                Format: postgresql://user:password@host:port/database

        Raises:
            ValueError: If connection_string is invalid
        """
        if not connection_string:
            raise ValueError("Connection string must be provided")

        self.connection_string = connection_string
        self.engine = create_engine(connection_string)
        self.Session = sessionmaker(bind=self.engine)
        self.init_db()

    def init_db(self) -> None:
        """Create the necessary tables if they don't exist."""
        Base.metadata.create_all(self.engine)

    def save_state(
        self,
        flow_uuid: str,
        method_name: str,
        state_data: dict[str, Any] | BaseModel,
    ) -> None:
        """Save the current flow state to PostgreSQL.

        Args:
            flow_uuid: Unique identifier for the flow instance
            method_name: Name of the method that just completed
            state_data: Current state data (either dict or Pydantic model)
        """
        state_dict = self._to_dict(state_data)

        with self.Session() as session:
            state = FlowState(
                flow_uuid=flow_uuid,
                method_name=method_name,
                timestamp=datetime.now(timezone.utc),
                state_json=state_dict,
            )
            session.add(state)
            session.commit()

    def load_state(self, flow_uuid: str) -> dict[str, Any] | None:
        """Load the most recent state for a given flow UUID.

        Args:
            flow_uuid: Unique identifier for the flow instance

        Returns:
            The most recent state as a dictionary, or None if no state exists
        """
        with self.Session() as session:
            state = (
                session.query(FlowState).filter(FlowState.flow_uuid == flow_uuid).order_by(FlowState.id.desc()).first()
            )

        if state:
            return state.state_json
        return None

    def save_pending_feedback(
        self,
        flow_uuid: str,
        context: PendingFeedbackContext,
        state_data: dict[str, Any] | BaseModel,
    ) -> None:
        """Save state with a pending feedback marker.

        This method stores both the flow state and the pending feedback context,
        allowing the flow to be resumed later when feedback is received.

        Args:
            flow_uuid: Unique identifier for the flow instance
            context: The pending feedback context with all resume information
            state_data: Current state data
        """
        state_dict = self._to_dict(state_data)

        self.save_state(flow_uuid, context.method_name, state_data)

        with self.Session() as session:
            existing = session.query(PendingFeedback).filter(PendingFeedback.flow_uuid == flow_uuid).first()

            if existing:
                existing.context_json = context.to_dict()
                existing.state_json = state_dict
                existing.created_at = datetime.now(timezone.utc)
            else:
                pending = PendingFeedback(
                    flow_uuid=flow_uuid,
                    context_json=context.to_dict(),
                    state_json=state_dict,
                    created_at=datetime.now(timezone.utc),
                )
                session.add(pending)

            session.commit()

    def load_pending_feedback(
        self,
        flow_uuid: str,
    ) -> tuple[dict[str, Any], PendingFeedbackContext] | None:
        """Load state and pending feedback context.

        Args:
            flow_uuid: Unique identifier for the flow instance

        Returns:
            Tuple of (state_data, pending_context) if pending feedback exists,
            None otherwise.
        """
        with self.Session() as session:
            pending = session.query(PendingFeedback).filter(PendingFeedback.flow_uuid == flow_uuid).first()

        if pending:
            context = PendingFeedbackContext.from_dict(pending.context_json)
            return (pending.state_json, context)
        return None

    def clear_pending_feedback(self, flow_uuid: str) -> None:
        """Clear the pending feedback marker after successful resume.

        Args:
            flow_uuid: Unique identifier for the flow instance
        """
        with self.Session() as session:
            session.query(PendingFeedback).filter(PendingFeedback.flow_uuid == flow_uuid).delete()
            session.commit()

    def _to_dict(self, state_data: dict[str, Any] | BaseModel) -> dict[str, Any]:
        """Convert state_data to dict.

        Args:
            state_data: Current state data (either dict or Pydantic model)

        Returns:
            Dictionary representation of state_data

        Raises:
            ValueError: If state_data is not a dict or Pydantic model
        """
        if isinstance(state_data, BaseModel):
            return state_data.model_dump()
        elif isinstance(state_data, dict):
            return state_data
        else:
            raise ValueError(f"state_data must be either a Pydantic BaseModel or dict, got {type(state_data)}")


if DATABASE_URL and DATABASE_URL.startswith("postgres"):
    logger.info("📊 Connecting persistence with postgres")
    persistence = PostgresFlowPersistence(connection_string=DATABASE_URL)
else:
    persistence = SQLiteFlowPersistence()
