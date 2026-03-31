"""Issue-related MCP tools."""

from pydantic import BaseModel, Field

from .base import ProjectManagementToolBase


class GetIssueSchema(BaseModel):
    """Input schema for get_issue tool."""

    issue_number: int = Field(..., description="Issue number")


class GetIssueTool(ProjectManagementToolBase):
    """Fetch an issue by number."""

    name: str = "get_issue"
    description: str = "Fetch an issue including body, labels, assignees, and state."
    args_schema: type[BaseModel] = GetIssueSchema

    def _run(self, issue_number: int) -> str:
        issue = self._pm.get_issue(issue_number)
        return issue.model_dump_json()


class ListIssuesSchema(BaseModel):
    """Input schema for list_issues tool."""



class ListIssuesTool(ProjectManagementToolBase):
    """List all open issues from repository."""

    name: str = "list_issues"
    description: str = "List all open issues, optionally filtered by label/milestone."
    args_schema: type[BaseModel] = ListIssuesSchema

    def _run(self) -> str:
        issues = self._pm.get_open_issues()
        return str([issue.model_dump() for issue in issues])


class AddIssueCommentSchema(BaseModel):
    """Input schema for add_issue_comment tool."""

    issue_number: int = Field(..., description="Issue number")
    body: str = Field(..., description="Comment text")


class AddIssueCommentTool(ProjectManagementToolBase):
    """Add a comment to an issue."""

    name: str = "add_issue_comment"
    description: str = "Post a comment to an issue. Used for progress updates and failure reports."
    args_schema: type[BaseModel] = AddIssueCommentSchema

    def _run(self, issue_number: int, body: str) -> str:
        success = self._pm.add_comment(issue_number, body)
        if not success:
            raise Exception(f"Failed to add comment to issue #{issue_number}")
        return "Comment added successfully"


class AssignIssueSchema(BaseModel):
    """Input schema for assign_issue tool."""

    issue_number: int = Field(..., description="Issue number")
    username: str | None = Field(None, description="Username to assign to (defaults to bot)")


class AssignIssueTool(ProjectManagementToolBase):
    """Assign an issue to a user during execution."""

    name: str = "assign_issue"
    description: str = "Assign issue to a user during execution."
    args_schema: type[BaseModel] = AssignIssueSchema

    def _run(self, issue_number: int, username: str | None = None) -> str:
        if username is None:
            username = self._pm.bot_username

        success = self._pm.assign_issue(issue_number, username)
        if not success:
            raise Exception(f"Failed to assign issue #{issue_number} to {username}")
        return f"Assigned to {username}"


class CloseIssueSchema(BaseModel):
    """Input schema for close_issue tool."""

    issue_number: int = Field(..., description="Issue number")


class CloseIssueTool(ProjectManagementToolBase):
    """Close issue on successful merge."""

    name: str = "close_issue"
    description: str = "Close issue on successful merge."
    args_schema: type[BaseModel] = CloseIssueSchema

    def _run(self, issue_number: int) -> str:
        success = self._pm.close_issue(issue_number)
        if not success:
            raise Exception(f"Failed to close issue #{issue_number}")
        return f"Closed issue #{issue_number}"
