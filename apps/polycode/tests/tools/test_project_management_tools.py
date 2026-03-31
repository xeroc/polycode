"""Test module for project management tools."""

from unittest.mock import MagicMock

from project_manager.base import ProjectManager
from tools.project_management.issues import GetIssueTool


def test_get_issue_tool():
    # Arrange
    mock_pm = MagicMock(spec=ProjectManager)
    mock_issue = MagicMock(
        id=42,
        number=42,
        title="Test issue",
        body="Test body",
        labels=["bug"],
    )
    mock_issue.model_dump_json.return_value = '{"id": 42}'
    mock_pm.get_issue.return_value = mock_issue

    # Act
    tool = GetIssueTool(project_manager=mock_pm)  # ty:ignore # pyright:ignore
    result = tool._run(issue_number=42)

    # Assert
    assert '"id": 42' in result
    mock_pm.get_issue.assert_called_once_with(42)
