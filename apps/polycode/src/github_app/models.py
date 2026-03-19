"""GitHub App database models using shared PostgreSQL base."""

from datetime import UTC, datetime
from typing import Any, Optional

from sqlalchemy import Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Boolean, DateTime, Integer, String, Text

from persistence.postgres import Base, JSONType

now = lambda: datetime.now(UTC)


class GitHubAppInstallation(Base):
    """GitHub App installation tracking."""

    __tablename__ = "github_app_installations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    installation_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    account_id: Mapped[int] = mapped_column(Integer, nullable=False)
    account_login: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    account_type: Mapped[str] = mapped_column(String(50), nullable=False)
    app_id: Mapped[int] = mapped_column(Integer, nullable=False)
    installation_token: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    repositories: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True)
    permissions: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True)
    events: Mapped[Optional[list[str]]] = mapped_column(JSONType, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=now,
        onupdate=now,
        nullable=False,
    )


class GitHubWebhookRegistration(Base):
    """Webhook registration tracking per installation."""

    __tablename__ = "github_webhook_registrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    webhook_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    installation_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    target_repo: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    events: Mapped[Optional[list[str]]] = mapped_column(JSONType, nullable=True)
    secret: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    webhook_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=now,
        onupdate=now,
        nullable=False,
    )


class LabelFlowMapping(Base):
    """Maps GitHub labels to CrewAI flow names."""

    __tablename__ = "label_flow_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    installation_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    label_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    flow_name: Mapped[str] = mapped_column(String(255), nullable=False)
    repo_pattern: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    config: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=now,
        onupdate=now,
        nullable=False,
    )


class FlowExecution(Base):
    """Flow execution tracking per installation."""

    __tablename__ = "flow_executions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    installation_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    repo_slug: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    issue_number: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    flow_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    trigger_label: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False, index=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    flow_metadata: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONType, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=now,
        onupdate=now,
        nullable=False,
    )

    __table_args__ = (
        Index("idx_flow_executions_installation", "installation_id"),
        Index("idx_flow_executions_status", "status"),
    )
