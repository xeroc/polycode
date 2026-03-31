"""Label-related MCP tools."""

from pydantic import BaseModel, Field

from .base import ProjectManagementToolBase


class ListLabelsSchema(BaseModel):
    """Input schema for list_labels tool."""



class ListLabelsTool(ProjectManagementToolBase):
    """Fetch all repo labels."""

    name: str = "list_labels"
    description: str = "Fetch all repository labels for discovery and management."
    args_schema: type[BaseModel] = ListLabelsSchema

    def _run(self) -> str:
        labels = self._pm.get_labels()
        return str(labels)


class CreateLabelSchema(BaseModel):
    """Input schema for create_label tool."""

    name: str = Field(..., description="Label name")
    color: str = Field(default="ffffff", description="Hex color code (6 chars)")
    description: str | None = Field(None, description="Label description")


class CreateLabelTool(ProjectManagementToolBase):
    """Create missing labels on first run."""

    name: str = "create_label"
    description: str = "Create a new repository label."
    args_schema: type[BaseModel] = CreateLabelSchema

    def _run(self, name: str, color: str = "ffffff", description: str | None = None) -> str:
        raise NotImplementedError("create_label not yet implemented in ProjectManager")


class AddLabelToIssueSchema(BaseModel):
    """Input schema for add_label_to_issue tool."""

    issue_number: int = Field(..., description="Issue number")
    labels: list[str] = Field(..., description="List of label names to add")


class AddLabelToIssueTool(ProjectManagementToolBase):
    """Apply status/flow labels to issue."""

    name: str = "add_label_to_issue"
    description: str = "Add labels to an issue (e.g., 'polycode:in-progress')."
    args_schema: type[BaseModel] = AddLabelToIssueSchema

    def _run(self, issue_number: int, labels: list[str]) -> str:
        success = self._pm.add_labels(issue_number, labels)
        if not success:
            raise Exception(f"Failed to add labels {labels} to issue #{issue_number}")
        return f"Added labels: {labels}"


class RemoveLabelFromIssueSchema(BaseModel):
    """Input schema for remove_label_from_issue tool."""

    issue_number: int = Field(..., description="Issue number")
    label: str = Field(..., description="Label name to remove")


class RemoveLabelFromIssueTool(ProjectManagementToolBase):
    """Clean up labels after flow completes."""

    name: str = "remove_label_from_issue"
    description: str = "Remove a label from an issue."
    args_schema: type[BaseModel] = RemoveLabelFromIssueSchema

    def _run(self, issue_number: int, label: str) -> str:
        success = self._pm.remove_label(issue_number, label)
        if not success:
            raise Exception(f"Failed to remove label '{label}' from issue #{issue_number}")
        return f"Removed label: {label}"
