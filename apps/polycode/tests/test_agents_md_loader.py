"""
Test AGENTS.md discovery and loading functionality.
"""

import tempfile
from pathlib import Path

from tools.agents_md_loader import AgentsMDLoaderTool


def test_agents_md_loader_tool():
    agents_md_map = {
        "AGENTS.md": "# Root AGENTS.md\n\nThis is the root file.",
        "src/crews/AGENTS.md": "# Crews AGENTS.md\n\nCrew-specific patterns.",
        "src/tools/AGENTS.md": "# Tools AGENTS.md\n\nTool-specific patterns.",
    }

    tool = AgentsMDLoaderTool(agents_md_map=agents_md_map)

    # Test loading root AGENTS.md
    result = tool._run("AGENTS.md")
    assert "Root AGENTS.md" in result
    assert "This is the root file." in result

    # Test loading subdirectory AGENTS.md
    result = tool._run("src/crews/AGENTS.md")
    assert "Crews AGENTS.md" in result
    assert "Crew-specific patterns." in result

    # Test non-existent file
    result = tool._run("nonexistent.md")
    assert "not found" in result
    assert "Available AGENTS.md files:" in result

    print("✓ All tests passed!")


def test_discovery_function():
    """Test the AGENTS.md discovery logic (simulated)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir_path = Path(tmpdir)

        # Create test AGENTS.md files
        (tmpdir_path / "AGENTS.md").write_text("# Root\n\nRoot content")
        (tmpdir_path / "src").mkdir()
        (tmpdir_path / "src" / "AGENTS.md").write_text("# Src\n\nSrc content")
        (tmpdir_path / "src" / "crews").mkdir()
        (tmpdir_path / "src" / "crews" / "AGENTS.md").write_text(
            "# Crews\n\nCrews content"
        )

        # Simulate discovery
        agents_md_map = {}
        for agents_file in tmpdir_path.rglob("AGENTS.md"):
            relative_path = str(agents_file.relative_to(tmpdir_path))
            content = agents_file.read_text()
            agents_md_map[relative_path] = content

        # Verify
        assert len(agents_md_map) == 3
        assert "AGENTS.md" in agents_md_map
        assert "src/AGENTS.md" in agents_md_map
        assert "src/crews/AGENTS.md" in agents_md_map

        print("✓ Discovery test passed!")


if __name__ == "__main__":
    test_agents_md_loader_tool()
    test_discovery_function()
    print("\n✓ All tests passed!")
