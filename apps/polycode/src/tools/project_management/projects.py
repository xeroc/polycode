"""Project board-related MCP tools."""

from typing import Literal

from pydantic import BaseModel, Field

from .base import ProjectManagementToolBase


class GetProjectItemSchema(BaseModel):
    """Input schema for get_project_item tool."""

    issue_number: int = Field(..., description="Issue number")


class GetProjectItemTool(ProjectManagementToolBase):
    """Fetch current status/fields for a project item."""

    name: str = "get_project_item"
    description: str = "Fetch current status and fields for a project item."
    args_schema: type[BaseModel] = GetProjectItemSchema

    def _run(self, issue_number: int) -> str:
        item = self._pm.find_project_item(issue_number)
        if not item:
            raise Exception(f"Project item not found for issue #{issue_number}")
        return item.model_dump_json()


class UpdateProjectItemStatusSchema(BaseModel):
    """Input schema for update_project_item_status tool."""

    issue_number: int = Field(..., description="Issue number")
    status: Literal["Todo", "Ready", "In Progress", "In Review", "Done", "Blocked"] = Field(
        ..., description="New status value"
    )


class UpdateProjectItemStatusTool(ProjectManagementToolBase):
    """Move a project board item to a new status column."""

    name: str = "update_project_item_status"
    description: str = "Move a project board item to a new status column (Todo -> In Progress -> Done)."
    args_schema: type[BaseModel] = UpdateProjectItemStatusSchema

    def _run(self, issue_number: int, status: str) -> str:
        success = self._pm.update_issue_status(issue_number, status)
        if not success:
            raise Exception(f"Failed to update issue #{issue_number} status to {status}")
        return f"Updated to {status}"


class AddItemToProjectSchema(BaseModel):
    """Input schema for add_item_to_project tool."""

    issue_number: int = Field(..., description="Issue number")


class AddItemToProjectTool(ProjectManagementToolBase):
    """Add a new issue to a project board."""

    name: str = "add_item_to_project"
    description: str = "Add a new issue to the project board."
    args_schema: type[BaseModel] = AddItemToProjectSchema

    def _run(self, issue_number: int) -> str:
        issue = self._pm.get_issue(issue_number)
        item_id = self._pm.add_issue_to_project(issue)
        if not item_id:
            raise Exception(f"Failed to add issue #{issue_number} to project")
        return f"Added to project with ID {item_id}"
