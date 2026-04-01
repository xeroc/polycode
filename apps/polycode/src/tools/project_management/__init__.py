"""Project management MCP tools for CrewAI agents.

Provides tools for issues, pull requests, project boards, and labels.
All tools are provider-agnostic via ProjectManager abstraction.
"""

from project_manager.base import ProjectManager

from .issues import (
    AddIssueCommentTool,
    AssignIssueTool,
    CloseIssueTool,
    GetIssueTool,
    ListIssuesTool,
)
from .labels import (
    AddLabelToIssueTool,
    CreateLabelTool,
    ListLabelsTool,
    RemoveLabelFromIssueTool,
)
from .projects import (
    AddItemToProjectTool,
    GetProjectItemTool,
    UpdateProjectItemStatusTool,
)
from .pull_requests import (
    CreatePullRequestTool,
    LinkPrToIssueTool,
    MergePullRequestTool,
)

PROJECT_TOOLS = [
    GetIssueTool,
    ListIssuesTool,
    AddIssueCommentTool,
    AssignIssueTool,
    CloseIssueTool,
    GetProjectItemTool,
    UpdateProjectItemStatusTool,
    AddItemToProjectTool,
    CreatePullRequestTool,
    MergePullRequestTool,
    LinkPrToIssueTool,
    ListLabelsTool,
    CreateLabelTool,
    AddLabelToIssueTool,
    RemoveLabelFromIssueTool,
]


def create_tools(project_manager: ProjectManager) -> list:
    """Create tool instances with injected ProjectManager.

    Args:
        project_manager: ProjectManager instance (created via ProjectManagerFactory)

    Returns:
        List of instantiated tool objects
    """
    return [tool_class(project_manager) for tool_class in PROJECT_TOOLS]  # ty:ignore
