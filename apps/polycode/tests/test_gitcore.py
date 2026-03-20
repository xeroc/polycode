"""Tests for gitcore module."""

from unittest.mock import MagicMock

from gitcore import (
    GitContext,
    GitcoreModule,
    WorktreeConfig,
    sanitize_branch_name,
)
from gitcore.operations import (
    get_commit_url,
)


def test_sanitize_branch_name_simple():
    assert sanitize_branch_name("Add new feature") == "add-new-feature"


def test_sanitize_branch_name_special_chars():
    assert sanitize_branch_name("Fix bug #123!") == "fix-bug-123"


def test_sanitize_branch_name_long():
    long_name = "This is a very long branch name that should be truncated"
    result = sanitize_branch_name(long_name)
    assert len(result) <= 16


def test_sanitize_branch_name_empty():
    assert sanitize_branch_name("") == "unnamed"


def test_worktree_config_defaults():
    config = WorktreeConfig(branch_name="test-branch")
    assert config.base_branch == "develop"
    assert "node_modules" in config.symlink_deps


def test_git_context_commit_url():
    ctx = GitContext(
        repo_path="/tmp/repo",
        repo_owner="acme",
        repo_name="project",
    )
    url = ctx.get_commit_url("abc123")
    assert url == "https://github.com/acme/project/commit/abc123"


def test_git_context_from_flow_state():
    mock_state = MagicMock()
    mock_state.path = "/repos/myrepo"
    mock_state.repo = "/repos/myrepo/.git/.worktrees/feature"
    mock_state.branch = "feature"
    mock_state.repo_owner = "owner"
    mock_state.repo_name = "repo"
    mock_state.project_config = None

    ctx = GitContext.from_flow_state(mock_state)

    assert ctx.repo_path == "/repos/myrepo"
    assert ctx.worktree_path == "/repos/myrepo/.git/.worktrees/feature"
    assert ctx.branch_name == "feature"
    assert ctx.installation_token is None


def test_git_context_from_flow_state_with_token():
    mock_state = MagicMock()
    mock_state.path = "/repos/myrepo"
    mock_state.repo = "/repos/myrepo/.git/.worktrees/feature"
    mock_state.branch = "feature"
    mock_state.repo_owner = "owner"
    mock_state.repo_name = "repo"

    mock_config = MagicMock()
    mock_config.token = "ghs_test_token_123"
    mock_state.project_config = mock_config

    ctx = GitContext.from_flow_state(mock_state)

    assert ctx.repo_path == "/repos/myrepo"
    assert ctx.installation_token == "ghs_test_token_123"
    assert ctx.project_config == mock_config


def test_get_commit_url():
    url = get_commit_url("acme", "project", "abc123")
    assert url == "https://github.com/acme/project/commit/abc123"


def test_gitcore_module_metadata():
    assert GitcoreModule.name == "gitcore"
    assert GitcoreModule.version == "0.1.0"
    assert GitcoreModule.dependencies == []


def test_gitcore_module_on_load():
    context = MagicMock()
    GitcoreModule.on_load(context)


def test_gitcore_module_register_hooks():
    pm = MagicMock()
    GitcoreModule.register_hooks(pm)


def test_gitcore_module_get_models():
    models = GitcoreModule.get_models()
    assert models == []
