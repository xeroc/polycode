"""Tests for project management tools."""

from unittest.mock import MagicMock

from project_manager.base import ProjectManager
from tools.project_management.issues import GetIssueTool
from tools.project_management.pull_requests import CreatePullRequestTool


def test_get_issue_tool_returns_json():
    mock_pm = MagicMock(spec=ProjectManager)
    mock_issue = MagicMock(
        id=42,
        number=42,
        title="Test issue",
        body="Test body",
        labels=["bug"],
    )
    mock_issue.model_dump_json.return_value = '{"id": 42, "title": "Test issue"}'
    mock_pm.get_issue.return_value = mock_issue

    tool = GetIssueTool(mock_pm)  # ty:ignore # pyright:ignore

    result = tool._run(issue_number=42)

    assert '"id": 42' in result
    assert '"title": "Test issue"' in result
    mock_pm.get_issue.assert_called_once_with(42)


def test_create_pull_request_tool():
    mock_pm = MagicMock(spec=ProjectManager)
    mock_pm.create_pull_request.return_value = (42, "https://github.com/owner/repo/pull/42")

    tool = CreatePullRequestTool(mock_pm)  # ty:ignore # pyright:ignore

    result = tool._run(
        title="Test PR",
        body="Test body",
        head="feature-branch",
        base="develop",
    )

    assert "Created PR #42" in result
    mock_pm.create_pull_request.assert_called_once_with("Test PR", "Test body", "feature-branch", "develop")
