"""Test retro module functionality."""

import subprocess
import tempfile
from pathlib import Path

from gitcore.types import GitContext
from retro import GitNotes
from retro.analyzer import PatternAnalyzer
from retro.types import RetroEntry


def _init_test_repo(tmpdir: Path) -> Path:
    repo = tmpdir / "test_repo"
    repo.mkdir()
    (repo / "test.txt").write_text("initial commit")
    subprocess.run(["git", "-C", str(repo), "init"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@test.com"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "Test"],
        check=True,
    )
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "initial"],
        check=True,
    )
    return repo


def test_git_notes_basic():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = _init_test_repo(Path(tmpdir))
        context = GitContext(repo_path=str(repo))
        notes = GitNotes(context)

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

        notes.add(model=retro)
        retrieved = notes.show(RetroEntry)

        assert retrieved is not None
        assert retrieved.retro_type == "success"
        assert "Test passed" in retrieved.what_worked


def test_pattern_analyzer():
    with tempfile.TemporaryDirectory() as tmpdir:
        repo = _init_test_repo(Path(tmpdir))
        context = GitContext(repo_path=str(repo))
        notes = GitNotes(context, notes_ref="refs/notes/retros")

        retro1 = RetroEntry(
            commit_sha="",
            flow_id="flow-1",
            repo_owner="test",
            repo_name="repo",
            retro_type="failure",
            what_failed=["Build timeout"],
            root_causes=["Long build process"],
            actionable_improvements=[],
        )

        subprocess.run(
            ["git", "-C", str(repo), "commit", "--allow-empty", "-m", "c2"],
            check=True,
        )
        retro2 = RetroEntry(
            commit_sha="",
            flow_id="flow-2",
            repo_owner="test",
            repo_name="repo",
            retro_type="failure",
            what_failed=["Build timeout"],
            root_causes=["Long build process"],
            actionable_improvements=[],
        )

        notes.add(model=retro1)
        notes.add(model=retro2)

        analyzer = PatternAnalyzer(repo_path=str(repo))
        trends = analyzer.analyze_recent_trends(limit=10)

        assert "common_failures" in trends
        assert len(trends["common_failures"]) > 0

        suggestions = analyzer.suggest_improvements_from_patterns(limit=5)
        assert len(suggestions) > 0
