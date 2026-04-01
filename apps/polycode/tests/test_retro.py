"""Tests for retro module."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from gitcore import GitNotes
from gitcore.types import GitContext
from retro.analyzer import PatternAnalyzer
from retro.hooks import RETRO_NOTES_REF, RetroHooks
from retro.module import RetroModule
from retro.types import RetroEntry


def _init_git_repo(path: Path) -> None:
    subprocess.run(
        ["git", "-C", str(path), "init"],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "test@test.com"],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "-C", str(path), "config", "user.name", "Test"],
        check=True,
        capture_output=True,
        text=True,
    )


def _commit(path: Path, message: str = "initial commit") -> str:
    subprocess.run(
        ["git", "-C", str(path), "commit", "--allow-empty", "-m", message],
        check=True,
        capture_output=True,
        text=True,
    )
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


class TestPatternAnalyzer:
    def test_load_retros_empty_repo(self, tmp_path):
        _init_git_repo(tmp_path)
        _commit(tmp_path)
        analyzer = PatternAnalyzer(repo_path=str(tmp_path))
        retros = analyzer._load_retros(limit=10)
        assert retros == []

    def test_load_retros_with_entries(self, tmp_path):
        _init_git_repo(tmp_path)
        context = GitContext(repo_path=str(tmp_path))
        notes = GitNotes(context, notes_ref=RETRO_NOTES_REF)
        retro1 = RetroEntry(
            commit_sha=_commit(tmp_path, "first"),
            flow_id="test-flow-1",
            repo_owner="testowner",
            repo_name="testrepo",
            retro_type="success",
            what_worked=["Tests passed"],
            what_failed=[],
        )
        notes.add(model=retro1, force=True)
        retro2 = RetroEntry(
            commit_sha=_commit(tmp_path, "second"),
            flow_id="test-flow-2",
            repo_owner="testowner",
            repo_name="testrepo",
            retro_type="failure",
            what_worked=[],
            what_failed=["Build timeout"],
        )
        notes.add(model=retro2, force=True)
        analyzer = PatternAnalyzer(repo_path=str(tmp_path))
        retros = analyzer._load_retros(limit=10)
        assert len(retros) == 2
        assert retros[0].retro_type == "failure"
        assert retros[1].retro_type == "success"

    def test_generate_context_injection_no_retros(self, tmp_path):
        _init_git_repo(tmp_path)
        _commit(tmp_path)
        analyzer = PatternAnalyzer(repo_path=str(tmp_path))
        ctx = analyzer.generate_context_injection(
            repo_owner="testowner",
            repo_name="testrepo",
        )
        assert ctx == ""

    def test_generate_context_injection_with_data(self, tmp_path):
        _init_git_repo(tmp_path)
        context = GitContext(repo_path=str(tmp_path))
        notes = GitNotes(context, notes_ref=RETRO_NOTES_REF)
        retro = RetroEntry(
            commit_sha=_commit(tmp_path, "c1"),
            flow_id="test-flow",
            repo_owner="testowner",
            repo_name="testrepo",
            retro_type="failure",
            what_worked=[],
            what_failed=["Build timeout"],
        )
        notes.add(model=retro, force=True)
        analyzer = PatternAnalyzer(repo_path=str(tmp_path))
        ctx = analyzer.generate_context_injection(
            repo_owner="testowner",
            repo_name="testrepo",
        )
        assert "Previous Retrospectives" in ctx
        assert "Build timeout" in ctx


class TestRetroHooks:
    def test_extract_successes_no_errors(self):
        hooks = RetroHooks()
        story = MagicMock()
        story.errors = []
        result = hooks._extract_successes(story)
        assert result == ["All tests passed"]

    def test_extract_successes_with_errors(self):
        hooks = RetroHooks()
        story = MagicMock()
        story.errors = ["some error"]
        result = hooks._extract_successes(story)
        assert result == []

    def test_get_head_sha(self, tmp_path):
        _init_git_repo(tmp_path)
        _commit(tmp_path)
        sha = RetroHooks._get_head_sha(str(tmp_path))
        assert len(sha) == 40
        assert all(c in "0123456789abcdef" for c in sha)


class TestRetroModule:
    def test_module_metadata(self):
        assert hasattr(RetroModule, "name")
        assert RetroModule.name == "retro"
        assert "gitcore" in RetroModule.dependencies

    def test_collect_retro_context_no_repo(self):
        state = MagicMock()
        state.repo = None
        result = RetroModule._collect_retro_context(state)
        assert result == {"retro_context": ""}

    def test_collect_retro_context_with_repo(self, tmp_path):
        _init_git_repo(tmp_path)
        _commit(tmp_path)
        state = MagicMock()
        state.repo = str(tmp_path)
        state.repo_owner = "testowner"
        state.repo_name = "testrepo"
        result = RetroModule._collect_retro_context(state)
        assert "retro_context" in result
        assert result["retro_context"] == ""

    def test_collect_retro_context_failure(self, tmp_path):
        state = MagicMock()
        state.repo = str(tmp_path)
        with patch(
            "retro.analyzer.PatternAnalyzer.generate_context_injection",
            side_effect=Exception("git error"),
        ):
            result = RetroModule._collect_retro_context(state)
        assert result == {"retro_context": ""}
