"""Tests for project_manager plugin integration."""

from unittest.mock import MagicMock

import pytest

from modules.hooks import FlowPhase
from project_manager import (
    ProjectManager,
    ProjectManagerModule,
)
from project_manager.hooks import ProjectManagerHooks
from project_manager.types import ProjectConfig


class MockProjectManager(ProjectManager):
    """Mock implementation for testing."""

    def __init__(self, config):
        super().__init__(config)
        self._bot_username = "test-bot"

    @property
    def bot_username(self) -> str:
        return self._bot_username

    def get_comments(self, issue_number: int) -> list:
        return []

    def get_last_comment_by_user(self, issue_number: int, username: str) -> int | None:
        return 123

    def update_comment(self, issue_number: int, comment_id: int, body: str) -> bool:
        return True

    def get_open_issues(self) -> list:
        return []

    def get_project_items(self) -> list:
        return []

    def add_issue_to_project(self, issue) -> str | None:
        return "item-123"

    def update_issue_status(self, issue_number: int, status: str) -> bool:
        return True

    def add_comment(self, issue_number: int, comment: str) -> bool:
        return True

    def has_label(self, issue_number: int, label_name: str) -> bool:
        return label_name == "approved"

    def merge_pull_request(
        self, pr_number: int, commit_message: str | None = None, merge_method: str = "merge"
    ) -> bool:
        return True


class TestProjectManagerModule:
    """Tests for ProjectManagerModule."""

    def test_module_metadata(self):
        assert ProjectManagerModule.name == "project_manager"
        assert ProjectManagerModule.version == "0.1.0"
        assert ProjectManagerModule.dependencies == []

    def test_module_on_load(self):
        context = MagicMock()
        ProjectManagerModule.on_load(context)

    def test_module_get_models(self):
        models = ProjectManagerModule.get_models()
        assert models == []


class TestProjectManagerHooks:
    """Tests for ProjectManagerHooks."""

    @pytest.fixture
    def mock_state(self):
        state = MagicMock()
        state.project_config = ProjectConfig(
            provider="github",
            repo_owner="testowner",
            repo_name="testrepo",
        )
        state.pr_number = None
        state.pr_url = None
        state.issue_id = 123
        state.planning_comment_id = None
        state.commit_urls = {}
        state.repo = "/tmp/repo"
        state.branch = "feature-branch"
        state.task = "Test task"
        state.commit_title = "feat: test"
        state.commit_message = "Test commit"
        state.commit_footer = ""
        return state

    @pytest.fixture
    def hooks(self):
        def factory(config):
            return MockProjectManager(config)

        return ProjectManagerHooks(factory)

    def test_hooks_skip_without_config(self, hooks):
        state = MagicMock()
        state.project_config = None

        hooks.on_flow_phase(FlowPhase.PRE_PR, "test-flow", state, None)

    def test_handle_planning_comment(self, hooks, mock_state):
        stories = [MagicMock(id=1, description="Story 1"), MagicMock(id=2, description="Story 2")]

        hooks.on_flow_phase(
            FlowPhase.PRE_PLANNING_COMMENT,
            "test-flow",
            mock_state,
            stories,
        )

        assert mock_state.planning_comment_id == 123

    def test_handle_update_checklist(self, hooks, mock_state):
        mock_state.planning_comment_id = 123

        data = {
            "stories": [MagicMock(id=1, description="Story 1")],
            "completed_ids": [1],
            "pr_url": "https://github.com/test/testrepo/pull/1",
            "merged": False,
        }

        hooks.on_flow_phase(
            FlowPhase.PRE_UPDATE_CHECKLIST,
            "test-flow",
            mock_state,
            data,
        )

    def test_handle_cleanup(self, hooks, mock_state):
        hooks.on_flow_phase(
            FlowPhase.POST_CLEANUP,
            "test-flow",
            mock_state,
            None,
        )

    def test_handle_review_start(self, hooks, mock_state):
        hooks.on_flow_phase(
            FlowPhase.PRE_REVIEW,
            "test-flow",
            mock_state,
            None,
        )


class TestFlowPhases:
    """Tests for new flow phases."""

    def test_planning_phases_exist(self):
        assert hasattr(FlowPhase, "PRE_PLANNING_COMMENT")
        assert hasattr(FlowPhase, "POST_PLANNING_COMMENT")
        assert hasattr(FlowPhase, "PRE_UPDATE_CHECKLIST")
        assert hasattr(FlowPhase, "POST_UPDATE_CHECKLIST")

    def test_phase_values(self):
        assert FlowPhase.PRE_PLANNING_COMMENT == "pre_planning_comment"
        assert FlowPhase.POST_PLANNING_COMMENT == "post_planning_comment"
        assert FlowPhase.PRE_UPDATE_CHECKLIST == "pre_update_checklist"
        assert FlowPhase.POST_UPDATE_CHECKLIST == "post_update_checklist"
