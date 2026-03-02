"""PostgreSQL-based flow state persistence using SQLAlchemy with JSONB."""

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel
from sqlalchemy import create_engine, Index, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from sqlalchemy.types import String, DateTime, Integer

from crewai.flow.persistence import FlowPersistence
from crewai.flow.async_feedback.types import PendingFeedbackContext


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""

    pass


class FlowState(Base):
    """Flow state table model."""

    __tablename__ = "flow_states"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    flow_uuid: Mapped[str] = mapped_column(String(255), nullable=False)
    method_name: Mapped[str] = mapped_column(String(255), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    state_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    __table_args__ = (Index("idx_flow_states_uuid", "flow_uuid"),)


class PendingFeedback(Base):
    """Pending feedback table model for async HITL."""

    __tablename__ = "pending_feedback"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    flow_uuid: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True
    )
    context_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    state_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

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
                session.query(FlowState)
                .filter(FlowState.flow_uuid == flow_uuid)
                .order_by(FlowState.id.desc())
                .first()
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
            existing = (
                session.query(PendingFeedback)
                .filter(PendingFeedback.flow_uuid == flow_uuid)
                .first()
            )

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
            pending = (
                session.query(PendingFeedback)
                .filter(PendingFeedback.flow_uuid == flow_uuid)
                .first()
            )

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
            session.query(PendingFeedback).filter(
                PendingFeedback.flow_uuid == flow_uuid
            ).delete()
            session.commit()

    def _to_dict(
        self, state_data: dict[str, Any] | BaseModel
    ) -> dict[str, Any]:
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
            raise ValueError(
                f"state_data must be either a Pydantic BaseModel or dict, got {type(state_data)}"
            )
