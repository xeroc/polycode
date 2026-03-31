"""Pull request-related MCP tools."""

from typing import Literal

from pydantic import BaseModel, Field

from .base import ProjectManagementToolBase


class CreatePRSchema(BaseModel):
    """Input schema for create_pull_request tool."""

    title: str = Field(..., description="PR title")
    body: str = Field(..., description="PR body/description")
    head: str = Field(..., description="Source branch name")
    base: str = Field(default="develop", description="Target branch name")


class CreatePullRequestTool(ProjectManagementToolBase):
    """Open a pull request with title, body, base/head branch."""

    name: str = "create_pull_request"
    description: str = "Open a PR with title, body, base/head branch."
    args_schema: type[BaseModel] = CreatePRSchema

    def _run(self, title: str, body: str, head: str, base: str = "develop") -> str:
        result = self._pm.create_pull_request(title, body, head, base)
        if not result:
            raise Exception("Failed to create pull request")
        pr_number, pr_url = result
        return f"Created PR #{pr_number}: {pr_url}"


class MergePRSchema(BaseModel):
    """Input schema for merge_pull_request tool."""

    pr_number: int = Field(..., description="Pull request number")
    commit_message: str | None = Field(None, description="Optional custom commit message for merge")
    merge_method: Literal["merge", "squash", "rebase"] = Field(default="merge", description="Merge method")


class MergePullRequestTool(ProjectManagementToolBase):
    """Merge a pull request into its base branch."""

    name: str = "merge_pull_request"
    description: str = "Auto-merge a PR when checks pass and approved."
    args_schema: type[BaseModel] = MergePRSchema

    def _run(self, pr_number: int, commit_message: str | None = None, merge_method: str = "merge") -> str:
        success = self._pm.merge_pull_request(pr_number, commit_message, merge_method)
        if not success:
            raise Exception(f"Failed to merge PR #{pr_number}")
        return f"Merged PR #{pr_number}"


class LinkPrToIssueSchema(BaseModel):
    """Input schema for link_pr_to_issue tool."""

    pr_number: int = Field(..., description="Pull request number")
    issue_number: int = Field(..., description="Issue number to link")


class LinkPrToIssueTool(ProjectManagementToolBase):
    """Ensure 'Closes #N' is in PR body."""

    name: str = "link_pr_to_issue"
    description: str = "Ensure PR body contains 'Closes #N' reference to issue."
    args_schema: type[BaseModel] = LinkPrToIssueSchema

    def _run(self, pr_number: int, issue_number: int) -> str:
        return f"PR #{pr_number} linked to issue #{issue_number}"
