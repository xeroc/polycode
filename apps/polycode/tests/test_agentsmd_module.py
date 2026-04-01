"""Tests for AgentsMDInjector and AgentsMDPolycodeModule."""

import tempfile
from pathlib import Path

from agentsmd.injector import AgentsMDInjector
from agentsmd.module import AgentsMDPolycodeModule


class FakeState:
    """Minimal state object for testing."""

    def __init__(self, repo: str = ""):
        self.repo = repo


def test_collect_empty_repo():
    """Test collect with non-existent repo returns empty values."""
    injector = AgentsMDInjector()
    state = FakeState(repo="/nonexistent/path")
    result = injector.collect(state)
    assert result["agents_md"] == ""
    assert result["agents_md_map"] == {}


def test_collect_no_repo_attribute():
    """Test collect with state lacking repo attribute."""
    injector = AgentsMDInjector()
    result = injector.collect(object())
    assert result["agents_md"] == ""
    assert result["agents_md_map"] == {}


def test_collect_discovers_agents_md():
    """Test collect discovers AGENTS.md files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        (tmpdir_path / "AGENTS.md").write_text("# Root\n\nRoot content")
        (tmpdir_path / "src").mkdir()
        (tmpdir_path / "src" / "AGENTS.md").write_text("# Src\n\nSrc content")

        injector = AgentsMDInjector()
        state = FakeState(repo=tmpdir)
        result = injector.collect(state)

        assert result["agents_md"] == "# Root\n\nRoot content"
        assert "AGENTS.md" in result["agents_md_map"]
        assert "src/AGENTS.md" in result["agents_md_map"]
        assert len(result["agents_md_map"]) == 2


def test_collect_no_root_uses_first():
    """Test that without root AGENTS.md, first found is used."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        (tmpdir_path / "src").mkdir()
        (tmpdir_path / "src" / "AGENTS.md").write_text("# Src\n\nSrc content")

        injector = AgentsMDInjector()
        state = FakeState(repo=tmpdir)
        result = injector.collect(state)

        assert result["agents_md"] == "# Src\n\nSrc content"
        assert "src/AGENTS.md" in result["agents_md_map"]


def test_collect_skips_hidden_dirs():
    """Test that hidden directories are skipped."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)
        (tmpdir_path / ".hidden").mkdir()
        (tmpdir_path / ".hidden" / "AGENTS.md").write_text("# Hidden")
        (tmpdir_path / "AGENTS.md").write_text("# Root")

        injector = AgentsMDInjector()
        state = FakeState(repo=tmpdir)
        result = injector.collect(state)

        assert ".hidden/AGENTS.md" not in result["agents_md_map"]
        assert "AGENTS.md" in result["agents_md_map"]


def test_injector_keys():
    """Test injector declares correct keys."""
    injector = AgentsMDInjector()
    assert injector.name == "agents_md"
    assert injector.keys == ["agents_md", "agents_md_map"]


def test_module_returns_injector():
    """Test module returns AgentsMDInjector."""
    injectors = AgentsMDPolycodeModule.get_context_injectors()
    assert len(injectors) == 1
    assert injectors[0].name == "agents_md"


def test_module_protocol_attrs():
    """Test module satisfies expected attributes."""
    assert AgentsMDPolycodeModule.name == "agentsmd"
    assert AgentsMDPolycodeModule.version == "0.1.0"
    assert AgentsMDPolycodeModule.dependencies == []
