"""Tests for project_manager plugin integration."""

from unittest.mock import MagicMock


from modules.hooks import FlowEvent
from project_manager import (
    ProjectManagerModule,
)
from project_manager.types import ProjectConfig


class TestFlowEvents:
    """Tests for flow events."""

    def test_event_types_exist(self):
        """Verify all FlowEvent types exist."""
        assert hasattr(FlowEvent, "FLOW_START")
        assert hasattr(FlowEvent, "FLOW_COMPLETE")
        assert hasattr(FlowEvent, "FLOW_ERROR")
        assert hasattr(FlowEvent, "GIT_COMMIT")
        assert hasattr(FlowEvent, "GIT_PUSH")
        assert hasattr(FlowEvent, "PR_CREATED")
        assert hasattr(FlowEvent, "PR_MERGED")
        assert hasattr(FlowEvent, "ISSUE_UPDATED")
        assert hasattr(FlowEvent, "WORKTREE_CLEANUP")
        assert hasattr(FlowEvent, "CHECKLIST_POSTED")
        assert hasattr(FlowEvent, "CHECKLIST_UPDATED")

    def test_event_values(self):
        """Verify event string values."""
        assert FlowEvent.FLOW_START == "flow_start"
        assert FlowEvent.FLOW_COMPLETE == "flow_complete"
        assert FlowEvent.FLOW_ERROR == "flow_error"
        assert FlowEvent.GIT_COMMIT == "git_commit"
        assert FlowEvent.GIT_PUSH == "git_push"
        assert FlowEvent.PR_CREATED == "pr_created"
        assert FlowEvent.PR_MERGED == "pr_merged"
        assert FlowEvent.ISSUE_UPDATED == "issue_updated"
        assert FlowEvent.WORKTREE_CLEANUP == "worktree_cleanup"
        assert FlowEvent.CHECKLIST_POSTED == "checklist_posted"
        assert FlowEvent.CHECKLIST_UPDATED == "checklist_updated"

    def test_label_parameter(self):
        """Test that events can have optional labels."""
        from modules.hooks import get_plugin_manager

        pm = get_plugin_manager()
        pm.hook.on_flow_event(
            event=FlowEvent.GIT_COMMIT,
            flow_id="test-flow",
            state=MagicMock(),
            result="abc123",
            label="implement",
        )


class TestProjectManagerModule:
    """Tests for ProjectManagerModule."""

    def test_module_metadata(self):
        """Verify module has required metadata."""
        assert hasattr(ProjectManagerModule, "name")
        assert ProjectManagerModule.name == "project_manager"
        assert hasattr(ProjectManagerModule, "version")

    def test_module_get_models(self):
        """Verify module returns models."""
        models = ProjectManagerModule.get_models()
        assert isinstance(models, list)
        assert len(models) >= 0


class TestProjectConfig:
    """Tests for ProjectConfig."""

    def test_config_creation(self):
        """Test creating a ProjectConfig."""
        config = ProjectConfig(
            provider="github",
            repo_owner="test-owner",
            repo_name="test-repo",
        )
        assert config.provider == "github"
        assert config.repo_owner == "test-owner"
        assert config.repo_name == "test-repo"

    def test_config_defaults(self):
        """Test ProjectConfig defaults."""
        config = ProjectConfig(
            provider="github",
            repo_owner="test-owner",
            repo_name="test-repo",
        )
        assert config.project_identifier is None
        assert config.token is None
        assert config.extra == {}


class TestPluginManager:
    """Tests for plugin manager setup."""

    def test_get_plugin_manager(self):
        """Verify plugin manager is properly configured."""
        from modules.hooks import get_plugin_manager

        pm = get_plugin_manager()
        assert pm is not None
        assert hasattr(pm, "hook")
