import os
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, MetaData, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlmodel import Field, Session, SQLModel, create_engine, select

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./feature_dev.db")


def _get_json_type():
    if DATABASE_URL.startswith("postgres"):
        return JSONB
    return JSON


JSONColumnType = _get_json_type()

_engine = None
_metadata = MetaData()


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(
            DATABASE_URL, echo=bool(os.getenv("DATABASE_ECHO", ""))
        )
    return _engine


engine = get_engine()


def init_db():
    SQLModel.metadata.create_all(engine)


class FlowExecution(SQLModel, table=True):
    __tablename__ = "flow_execution"
    __table_args__ = {"extend_existing": True}

    id: int | None = Field(default=None, primary_key=True)
    flow_id: str = Field(index=True, unique=True)
    issue_id: int = Field(default=0)
    task: str = Field(default="")
    repo: str = Field(default="")
    branch: str = Field(default="")
    current_phase: str = Field(default="")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    build_cmd: str | None = Field(default=None)
    test_cmd: str | None = Field(default=None)
    ci_notes: str | None = Field(default=None)
    baseline: str | None = Field(default=None)
    findings: str | None = Field(default=None)

    current_story_id: int | None = Field(default=None)
    current_story_title: str | None = Field(default=None)
    current_story_description: str | None = Field(default=None)
    current_story_acceptance_criteria: dict | None = Field(
        default=None, sa_type=JSONColumnType
    )

    verified: bool = Field(default=False)
    tested: bool = Field(default=False)

    pr_url: str | None = Field(default=None)
    pr_number: int | None = Field(default=None)
    review_status: str | None = Field(default=None)
    diff: str | None = Field(
        default=None, sa_column=Column(Text, nullable=True)
    )

    commit_title: str | None = Field(default=None)
    commit_message: str | None = Field(default=None)
    commit_footer: str | None = Field(default=None)

    changes: list | None = Field(default=None, sa_type=JSONColumnType)
    tests: list | None = Field(default=None, sa_type=JSONColumnType)


class Story(SQLModel, table=True):
    __tablename__ = "story"
    __table_args__ = {"extend_existing": True}

    id: int | None = Field(default=None, primary_key=True)
    flow_db_id: int = Field(foreign_key="flow_execution.id")
    story_id: int = Field()
    title: str = Field()
    description: str = Field(default="")
    acceptance_criteria: list = Field(
        default_factory=list, sa_type=JSONColumnType
    )
    order: int = Field(default=0)
    completed: bool = Field(default=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class PhaseSnapshot(SQLModel, table=True):
    __tablename__ = "phase_snapshot"
    __table_args__ = {"extend_existing": True}

    id: int | None = Field(default=None, primary_key=True)
    flow_db_id: int = Field(foreign_key="flow_execution.id")
    phase: str = Field()
    state_json: dict = Field(sa_type=JSONColumnType)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class WebhookConfig(SQLModel, table=True):
    __tablename__ = "webhook_config"
    __table_args__ = {"extend_existing": True}

    id: int | None = Field(default=None, primary_key=True)
    name: str = Field()
    url: str
    events: list = Field(default_factory=list, sa_type=JSONColumnType)
    active: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


def save_state_snapshot(
    flow_id: str, phase: str, state: dict[str, Any]
) -> PhaseSnapshot | None:
    with Session(engine) as session:
        flow = session.exec(
            select(FlowExecution).where(FlowExecution.flow_id == flow_id)
        ).first()
        if not flow:
            return None

        snapshot = PhaseSnapshot(
            flow_db_id=flow.id,
            phase=phase,
            state_json=state,
        )
        session.add(snapshot)
        session.commit()
        session.refresh(snapshot)
        return snapshot


def get_or_create_flow(flow_id: str, state: dict[str, Any]) -> FlowExecution:
    with Session(engine) as session:
        flow = session.exec(
            select(FlowExecution).where(FlowExecution.flow_id == flow_id)
        ).first()
        if flow:
            return flow

        flow = FlowExecution(
            flow_id=flow_id,
            issue_id=state.get("issue_id", 0),
            task=state.get("task", ""),
            repo=state.get("repo", ""),
            branch=state.get("branch", ""),
        )
        session.add(flow)
        session.commit()
        session.refresh(flow)
        return flow


def upsert_stories(flow_id: str, stories: list[dict]) -> list[Story]:
    with Session(engine) as session:
        flow = session.exec(
            select(FlowExecution).where(FlowExecution.flow_id == flow_id)
        ).first()
        if not flow:
            return []

        created_stories = []
        for order, story_data in enumerate(stories):
            story = Story(
                flow_db_id=flow.id,
                story_id=story_data.get("id", 0),
                title=story_data.get("title", ""),
                description=story_data.get("description", ""),
                acceptance_criteria=story_data.get("acceptance_criteria", []),
                order=order,
            )
            session.add(story)
            session.flush()
            created_stories.append(story)

        session.commit()
        return created_stories


def mark_story_completed(flow_id: str, story_id: int) -> Story | None:
    with Session(engine) as session:
        flow = session.exec(
            select(FlowExecution).where(FlowExecution.flow_id == flow_id)
        ).first()
        if not flow:
            return None

        story = session.exec(
            select(Story).where(
                Story.flow_db_id == flow.id, Story.story_id == story_id
            )
        ).first()
        if not story:
            return None

        story.completed = True
        session.add(story)
        session.commit()
        session.refresh(story)
        return story


def update_flow_state(
    flow_id: str, state: dict[str, Any], phase: str
) -> FlowExecution:
    with Session(engine) as session:
        flow = session.exec(
            select(FlowExecution).where(FlowExecution.flow_id == flow_id)
        ).first()
        if not flow:
            flow = FlowExecution(
                flow_id=flow_id,
                issue_id=state.get("issue_id", 0),
                task=state.get("task", ""),
                repo=state.get("repo", ""),
                branch=state.get("branch", ""),
            )
            session.add(flow)
            session.flush()

        flow.current_phase = phase
        flow.updated_at = datetime.now(timezone.utc)

        for key in [
            "build_cmd",
            "test_cmd",
            "ci_notes",
            "baseline",
            "findings",
            "current_story_id",
            "current_story_title",
            "pr_url",
            "pr_number",
            "review_status",
            "diff",
            "commit_title",
            "commit_message",
            "commit_footer",
            "changes",
            "tests",
        ]:
            if key in state and state[key] is not None:
                setattr(flow, key, state[key])

        for bool_key in ["verified", "tested"]:
            if bool_key in state:
                setattr(flow, bool_key, state[bool_key])

        session.add(flow)
        session.commit()
        session.refresh(flow)
        return flow


def get_latest_state(flow_id: str) -> PhaseSnapshot | None:
    with Session(engine) as session:
        flow = session.exec(
            select(FlowExecution).where(FlowExecution.flow_id == flow_id)
        ).first()
        if not flow:
            return None
        statement = (
            select(PhaseSnapshot)
            .where(PhaseSnapshot.flow_db_id == flow.id)
            .order_by(PhaseSnapshot.created_at.desc())
        )
        return session.exec(statement).first()


def get_active_webhooks() -> list[WebhookConfig]:
    with Session(engine) as session:
        statement = select(WebhookConfig).where(WebhookConfig.active.is_(True))
        return list(session.exec(statement))
