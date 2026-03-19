"""PostgreSQL persistence for retrospectives."""

import logging
from datetime import datetime

from sqlalchemy import Index, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .types import RetroEntry, RetroQuery

log = logging.getLogger(__name__)

DATABASE_URL = None
engine = None
SessionLocal = None


def init_db(database_url: str) -> None:
    """Initialize retro database connection.

    Args:
        database_url: PostgreSQL connection string
    """
    global DATABASE_URL, engine, SessionLocal
    DATABASE_URL = database_url
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    log.info("📊 Retro database initialized")


class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""


class RetroModel(Base):
    """Retro database model."""

    __tablename__ = "retrospectives"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    commit_sha: Mapped[str] = mapped_column()
    flow_id: Mapped[str] = mapped_column()
    story_id: Mapped[int | None] = mapped_column()
    story_title: Mapped[str | None] = mapped_column()
    repo_owner: Mapped[str] = mapped_column()
    repo_name: Mapped[str] = mapped_column()
    retro_type: Mapped[str] = mapped_column()
    what_worked: Mapped[str] = mapped_column()
    what_failed: Mapped[str] = mapped_column()
    root_causes: Mapped[str] = mapped_column()
    actionable_improvements: Mapped[str] = mapped_column()
    time_to_completion_seconds: Mapped[int | None] = mapped_column()
    retry_count: Mapped[int] = mapped_column()
    test_coverage_impact: Mapped[float | None] = mapped_column()
    build_duration_ms: Mapped[int | None] = mapped_column()
    test_duration_ms: Mapped[int | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=text("CURRENT_TIMESTAMP"))

    __table_args__ = (
        Index("idx_retro_commit", "commit_sha"),
        Index("idx_retro_repo", "repo_owner", "repo_name"),
        Index("idx_retro_type", "retro_type"),
        Index("idx_retro_created", "created_at"),
    )


def retro_model_to_entry(model: RetroModel) -> RetroEntry:
    """Convert database model to RetroEntry.

    Args:
        model: RetroModel instance

    Returns:
        RetroEntry instance
    """
    import json

    return RetroEntry(
        commit_sha=model.commit_sha,
        flow_id=model.flow_id,
        story_id=model.story_id,
        story_title=model.story_title,
        repo_owner=model.repo_owner,
        repo_name=model.repo_name,
        timestamp=model.created_at,
        retro_type=model.retro_type,
        what_worked=json.loads(model.what_worked),
        what_failed=json.loads(model.what_failed),
        root_causes=json.loads(model.root_causes),
        actionable_improvements=json.loads(model.actionable_improvements),
        time_to_completion_seconds=model.time_to_completion_seconds,
        retry_count=model.retry_count,
        test_coverage_impact=model.test_coverage_impact,
        build_duration_ms=model.build_duration_ms,
        test_duration_ms=model.test_duration_ms,
    )


class RetroStore:
    """Retro storage with PostgreSQL and git-notes sync."""

    def __init__(self, session: sessionmaker) -> None:
        """Initialize retro store.

        Args:
            session: SQLAlchemy session factory
        """
        if not SessionLocal:
            raise RuntimeError("RetroStore not initialized. Call init_db() first.")
        self.session_factory = session

    def create_tables(self) -> None:
        """Create retrospectives table."""
        if engine:
            Base.metadata.create_all(bind=engine)
        log.info("📋 Created retrospectives table")

    def store(self, retro: RetroEntry) -> None:
        """Store retrospective in database.

        Args:
            retro: RetroEntry to store
        """
        import json

        model = RetroModel(
            commit_sha=retro.commit_sha,
            flow_id=retro.flow_id,
            story_id=retro.story_id,
            story_title=retro.story_title,
            repo_owner=retro.repo_owner,
            repo_name=retro.repo_name,
            retro_type=retro.retro_type,
            what_worked=json.dumps(retro.what_worked),
            what_failed=json.dumps(retro.what_failed),
            root_causes=json.dumps(retro.root_causes),
            actionable_improvements=json.dumps([item.model_dump() for item in retro.actionable_improvements]),
            time_to_completion_seconds=retro.time_to_completion_seconds,
            retry_count=retro.retry_count,
            test_coverage_impact=retro.test_coverage_impact,
            build_duration_ms=retro.build_duration_ms,
            test_duration_ms=retro.test_duration_ms,
        )

        with self.session_factory() as sess:
            sess.add(model)
            sess.commit()
            log.info(f"💾 Stored retro for {retro.commit_sha[:8]} in database")

    def get_by_commit(self, commit_sha: str) -> RetroEntry | None:
        """Get retrospective by commit SHA.

        Args:
            commit_sha: Commit SHA to query

        Returns:
            RetroEntry or None
        """
        with self.session_factory() as sess:
            model = sess.query(RetroModel).filter(RetroModel.commit_sha == commit_sha).first()
            if not model:
                return None
            return retro_model_to_entry(model)

    def query(self, params: RetroQuery) -> list[RetroEntry]:
        """Query retrospectives with filters.

        Args:
            params: Query parameters

        Returns:
            List of RetroEntry
        """
        with self.session_factory() as sess:
            query = sess.query(RetroModel)

            if params.repo_owner:
                query = query.filter(RetroModel.repo_owner == params.repo_owner)
            if params.repo_name:
                query = query.filter(RetroModel.repo_name == params.repo_name)
            if params.retro_type:
                query = query.filter(RetroModel.retro_type == params.retro_type)
            if params.since:
                query = query.filter(RetroModel.created_at >= params.since)

            query = query.order_by(RetroModel.created_at.desc())
            query = query.limit(params.limit)

            models = query.all()
            return [retro_model_to_entry(m) for m in models]

    def get_recent_failures(self, limit: int = 10) -> list[RetroEntry]:
        """Get recent failure retrospectives.

        Args:
            limit: Maximum results

        Returns:
            List of failure retros
        """
        params = RetroQuery(retro_type="failure", limit=limit)
        return self.query(params)

    def get_top_issues(self, limit: int = 10) -> dict[str, int]:
        """Extract top recurring issues from retros.

        Args:
            limit: Maximum results to analyze

        Returns:
            Dict mapping issue to count
        """
        from collections import Counter

        with self.session_factory() as sess:
            models = (
                sess.query(RetroModel)
                .filter(RetroModel.retro_type == "failure")
                .order_by(RetroModel.created_at.desc())
                .limit(limit * 2)
                .all()
            )

            all_issues: list[str] = []
            for m in models:
                retro = retro_model_to_entry(m)
                all_issues.extend(retro.what_failed)

            counter = Counter(all_issues)
            return dict(counter.most_common(limit))

    def delete(self, commit_sha: str) -> bool:
        """Delete retrospective by commit SHA.

        Args:
            commit_sha: Commit SHA to delete

        Returns:
            True if deleted, False otherwise
        """
        with self.session_factory() as sess:
            result = sess.query(RetroModel).filter(RetroModel.commit_sha == commit_sha).delete()
            sess.commit()
            deleted = result > 0
            if deleted:
                log.info(f"🗑️ Deleted retro for {commit_sha[:8]}")
            return deleted
