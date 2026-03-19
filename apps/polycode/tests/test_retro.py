"""Test retro module functionality."""

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from retro import GitNotes, init_db

import subprocess

from retro.persistence import RetroStore
from retro.types import RetroEntry

DATABASE_URL = "sqlite:///test_retro.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

init_db(DATABASE_URL)
store = RetroStore(SessionLocal)
store.create_tables()


def test_git_notes_basic():
    """Test basic GitNotes operations."""
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmpdir:
        test_repo = Path(tmpdir) / "test_repo"

        test_repo.mkdir()
        (test_repo / "test.txt").write_text("initial commit")

        subprocess.run(
            ["git", "-C", str(test_repo), "init"],
            check=True,
        )

        subprocess.run(
            ["git", "-C", str(test_repo), "add", "."],
            check=True,
        )

        subprocess.run(
            ["git", "-C", str(test_repo), "commit", "-m", "initial"],
            check=True,
        )

        notes = GitNotes(str(test_repo))

        retro = RetroEntry(
            commit_sha="",
            flow_id="test-flow",
            repo_owner="test",
            repo_name="repo",
            retro_type="success",
            what_worked=["Test passed"],
            what_failed=[],
            root_causes=[],
            actionable_improvements=[],
        )

        notes.add(retro=retro)
        retrieved = notes.show(commit_sha=None)

        assert retrieved is not None
        assert retrieved.retro_type == "success"
        assert "Test passed" in retrieved.what_worked


def test_persistence_basic():
    """Test basic RetroStore operations."""

    retro = RetroEntry(
        commit_sha="abc123",
        flow_id="test-flow",
        repo_owner="test",
        repo_name="repo",
        retro_type="failure",
        what_worked=["Nothing"],
        what_failed=["Tests failed"],
        root_causes=["Missing dependency"],
        actionable_improvements=[],
    )

    store.store(retro=retro)

    retrieved = store.get_by_commit("abc123")

    assert retrieved is not None
    assert retrieved.commit_sha == "abc123"
    assert retrieved.retro_type == "failure"
    assert "Tests failed" in retrieved.what_failed


def test_pattern_analyzer():
    """Test PatternAnalyzer functionality."""
    from retro.analyzer import PatternAnalyzer

    analyzer = PatternAnalyzer(store=store)

    test_retro_1 = RetroEntry(
        commit_sha="sha1",
        flow_id="flow-1",
        repo_owner="test",
        repo_name="repo",
        retro_type="failure",
        what_failed=["Build timeout"],
        root_causes=["Long build process"],
        actionable_improvements=[],
    )

    test_retro_2 = RetroEntry(
        commit_sha="sha2",
        flow_id="flow-1",
        repo_owner="test",
        repo_name="repo",
        retro_type="failure",
        what_failed=["Build timeout"],
        root_causes=["Long build process"],
        actionable_improvements=[],
    )

    store.store(retro=test_retro_1)
    store.store(retro=test_retro_2)

    trends = analyzer.analyze_recent_trends(limit=10)

    assert "common_failures" in trends
    assert len(trends["common_failures"]) > 0

    suggestions = analyzer.suggest_improvements_from_patterns(limit=5)
    assert len(suggestions) > 0
