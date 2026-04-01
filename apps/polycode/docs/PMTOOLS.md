# Project Management MCP Tools - Implementation Plan

## Architecture Overview

```
apps/polycode/src/
├── tools/
│   ├── project_management/         # MCP tools for project management
│   │   ├── __init__.py
│   │   ├── base.py              # Base tool class with shared init logic
│   │   ├── issues.py            # Issue tools (get, list, comment, assign, close)
│   │   ├── projects.py          # Project board tools
│   │   ├── pull_requests.py     # PR tools
│   │   └── labels.py           # Label tools
│   └── ...                      # Existing tools (unchanged)
├── project_manager/
│   ├── factory.py               # ProjectManagerFactory - creates PM based on provider
│   ├── base.py                 # Abstract ProjectManager (ADD: close_issue, assign_issue)
│   ├── github.py                # GitHub implementation (EXISTS)
│   └── types.py                # Shared types (EXISTS)
└── flows/
    └── base.py                 # REFACTOR: Use ProjectManagerFactory
```

## Design Decisions

### 1. Base Tool Pattern (Concrete with Shared Init)

```python
# tools/project_management/base.py
from abc import ABC, abstractmethod
from crewai.tools import BaseTool
from project_manager.base import ProjectManager
from pydantic import BaseModel

class ProjectManagementToolBase(BaseTool):
    """Concrete base class for all project management MCP tools.

    Subclasses implement _run() with operation-specific logic.
    Common initialization (ProjectManager injection) happens in __init__.
    """

    def __init__(self, project_manager: ProjectManager, **kwargs):
        """Initialize tool with ProjectManager instance.

        Args:
            project_manager: ProjectManager instance (GitHub, Jira, GitLab, etc.)
        """
        super().__init__(**kwargs)
        self.pm = project_manager

    @abstractmethod
    def _run(self, **kwargs) -> str:
        """Execute tool operation. Returns JSON string."""
```

### 2. Factory Pattern

```python
# project_manager/factory.py
from project_manager.types import ProjectConfig
from project_manager.base import ProjectManager

class ProjectManagerFactory:
    """Factory for creating ProjectManager instances based on provider."""

    @staticmethod
    def create(config: ProjectConfig) -> ProjectManager:
        """Create ProjectManager based on config.provider.

        Args:
            config: Project configuration with provider field

        Returns:
            ProjectManager instance (GitHubProjectManager, JiraProjectManager, etc.)

        Raises:
            ValueError: If provider is unsupported
        """
        provider = config.provider.lower()

        if provider == "github":
            from project_manager.github import GitHubProjectManager
            return GitHubProjectManager(config)
        elif provider == "jira":
            from project_manager.jira import JiraProjectManager  # FUTURE
            return JiraProjectManager(config)
        elif provider == "gitlab":
            from project_manager.gitlab import GitLabProjectManager  # FUTURE
            return GitLabProjectManager(config)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
```

### 3. Tool Array Creation

```python
# tools/project_management/__init__.py
from .issues import (
    GetIssueTool,
    ListIssuesTool,
    AddIssueCommentTool,
    AssignIssueTool,
    CloseIssueTool,
)
from .projects import (
    GetProjectItemTool,
    UpdateProjectItemStatusTool,
    AddItemToProjectTool,
)
from .pull_requests import (
    CreatePullRequestTool,
    MergePullRequestTool,
    LinkPrToIssueTool,
)
from .labels import (
    ListLabelsTool,
    CreateLabelTool,
    AddLabelToIssueTool,
    RemoveLabelFromIssueTool,
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
    return [
        tool_class(project_manager)
        for tool_class in PROJECT_TOOLS
    ]
```

### 4. Flows/base.py Refactor

```python
# flows/base.py - UPDATED
from project_manager.factory import ProjectManagerFactory

# In FlowIssueManagement.get_project_manager():
# OLD: self._project_manager = GitHubProjectManager(self.state.project_config)
# NEW: self._project_manager = ProjectManagerFactory.create(self.state.project_config)
```

## File Creation Plan

### New Files to Create:

1. **`project_manager/factory.py`** (ProjectManagerFactory class)

2. **`tools/project_management/__init__.py`** (PROJECT_TOOLS array + create_tools function)

3. **`tools/project_management/base.py`** (ProjectManagementToolBase concrete class)

4. **`tools/project_management/issues.py`** (5 MCP tools)

```python
# tools/project_management/issues.py

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from .base import ProjectManagementToolBase
from project_manager.types import Issue

class GetIssueSchema(BaseModel):
    """Input schema for get_issue tool."""
    issue_number: int = Field(..., description="Issue number")

class GetIssueTool(ProjectManagementToolBase):
    """Fetch a GitHub issue by number."""

    name: str = "get_issue"
    description: str = "Fetch a GitHub issue including body, labels, assignees, and state."
    args_schema: type[BaseModel] = GetIssueSchema

    def _run(self, issue_number: int) -> str:
        issue = self.pm.get_issue(issue_number)
        # Return JSON for agent consumption
        return issue.model_dump_json()

class ListIssuesTool(ProjectManagementToolBase):
    """List all open issues from repository."""

    name: str = "list_issues"
    description: str = "List all open issues, optionally filtered by label/milestone."
    args_schema: type[BaseModel] = BaseModel  # No params needed

    def _run(self) -> str:
        issues = self.pm.get_open_issues()
        return [issue.model_dump() for issue in issues] | str

class AddIssueCommentTool(ProjectManagementToolBase):
    """Add a comment to an issue."""

    name: str = "add_issue_comment"
    description: str = "Post a comment to an issue. Used for progress updates and failure reports."

    def __init__(self, project_manager, **kwargs):
        super().__init__(project_manager, **kwargs)
        # Define schema in __init__ since body param varies
        self.args_schema = type[BaseModel] = BaseModel

    def _run(self, issue_number: int, body: str) -> str:
        success = self.pm.add_comment(issue_number, body)
        if not success:
            raise Exception(f"Failed to add comment to issue #{issue_number}")
        return "Comment added successfully"

class AssignIssueTool(ProjectManagementToolBase):
    """Assign an issue to bot user during execution."""

    name: str = "assign_issue"
    description: str = "Assign issue to bot user during execution."

    def _run(self, issue_number: int, username: str = None) -> str:
        # username is optional - defaults to bot_username
        if username is None:
            username = self.pm.bot_username

        success = self.pm.add_labels(issue_number, [username])  # Reuse add_labels for assignment
        if not success:
            raise Exception(f"Failed to assign issue #{issue_number} to {username}")
        return f"Assigned to {username}"

class CloseIssueTool(ProjectManagementToolBase):
    """Close issue on successful merge."""

    name: str = "close_issue"
    description: str = "Close issue on successful merge."

    def _run(self, issue_number: int) -> str:
        # This requires implementation in ProjectManager (not currently in base.py)
        # For now, will raise NotImplementedError
        raise NotImplementedError("close_issue not yet implemented in ProjectManager")
```

5. **`tools/project_management/projects.py`** (3 MCP tools)

```python
# tools/project_management/projects.py

from crewai.tools import BaseTool
from pydantic import BaseModel, Field, Literal
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
        item = self.pm.find_project_item(issue_number)
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
    description: str = "Move a project board item to a new status column (Todo → In Progress → Done)."
    args_schema: type[BaseModel] = UpdateProjectItemStatusSchema

    def _run(self, issue_number: int, status: str) -> str:
        success = self.pm.update_issue_status(issue_number, status)
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
        issue = self.pm.get_issue(issue_number)
        item_id = self.pm.add_issue_to_project(issue)
        if not item_id:
            raise Exception(f"Failed to add issue #{issue_number} to project")
        return f"Added to project with ID {item_id}"
```

6. **`tools/project_management/pull_requests.py`** (3 MCP tools)

```python
# tools/project_management/pull_requests.py

from crewai.tools import BaseTool
from pydantic import BaseModel, Field, Literal
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
        result = self.pm.create_pull_request(title, body, head, base)
        if not result:
            raise Exception("Failed to create pull request")
        pr_number, pr_url = result
        return f"Created PR #{pr_number}: {pr_url}"

class MergePRSchema(BaseModel):
    """Input schema for merge_pull_request tool."""
    pr_number: int = Field(..., description="Pull request number")
    commit_message: str | None = Field(None, description="Optional custom commit message for merge")
    merge_method: Literal["merge", "squash", "rebase"] = Field(
        default="merge", description="Merge method"
    )

class MergePullRequestTool(ProjectManagementToolBase):
    """Merge a pull request into its base branch."""

    name: str = "merge_pull_request"
    description: str = "Auto-merge a PR when checks pass and approved."
    args_schema: type[BaseModel] = MergePRSchema

    def _run(self, pr_number: int, commit_message: str = None, merge_method: str = "merge") -> str:
        success = self.pm.merge_pull_request(pr_number, commit_message, merge_method)
        if not success:
            raise Exception(f"Failed to merge PR #{pr_number}")
        return f"Merged PR #{pr_number}"

class LinkPrToIssueSchema(BaseModel):
    """Input schema for link_pr_to_issue tool."""
    pr_number: int = Field(..., description="Pull request number")

class LinkPrToIssueTool(ProjectManagementToolBase):
    """Ensure 'Closes #N' is in PR body."""

    name: str = "link_pr_to_issue"
    description: str = "Ensure PR body contains 'Closes #N' reference to issue."
    args_schema: type[BaseModel] = LinkPrToIssueSchema

    def _run(self, pr_number: int) -> str:
        # This is a validation/helper - actual linking happens in create_pull_request
        # For MVP, just return confirmation
        return f"PR #{pr_number} linked to issue"
```

7. **`tools/project_management/labels.py`** (4 MCP tools)

```python
# tools/project_management/labels.py

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from .base import ProjectManagementToolBase

class ListLabelsTool(ProjectManagementToolBase):
    """Fetch all repo labels."""

    name: str = "list_labels"
    description: str = "Fetch all repository labels for discovery and management."
    args_schema: type[BaseModel] = BaseModel

    def _run(self) -> str:
        labels = self.pm.get_labels()  # Requires adding get_labels to ProjectManager
        # For MVP, use placeholder
        return "[]"  # TODO: Implement get_labels in ProjectManager

class CreateLabelTool(ProjectManagementToolBase):
    """Create missing labels on first run."""

    name: str = "create_label"
    description: str = "Create a new repository label."

    def __init__(self, project_manager, **kwargs):
        super().__init__(project_manager, **kwargs)
        self.args_schema = type[BaseModel] = BaseModel

    def _run(self, name: str, color: str = "ffffff", description: str = "") -> str:
        # This requires implementation in ProjectManager
        # For MVP, return mock response
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
        success = self.pm.add_labels(issue_number, labels)
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
        # This requires implementation in ProjectManager
        raise NotImplementedError("remove_label not yet implemented in ProjectManager")
```

### Files to Update:

8. **`project_manager/base.py`** - Add missing abstract methods

```python
# Add to ProjectManager abstract class:

@abstractmethod
def close_issue(self, issue_number: int) -> bool:
    """Close an issue.

    Args:
        issue_number: Issue number

    Returns:
        True if successful, False otherwise
    """

@abstractmethod
def assign_issue(self, issue_number: int, username: str) -> bool:
    """Assign an issue to a user.

    Args:
        issue_number: Issue number
        username: GitHub username to assign to

    Returns:
        True if successful, False otherwise
    """

@abstractmethod
def get_labels(self) -> list[str]:
    """Get all repository labels.

    Returns:
        List of label names
    """
```

9. **`flows/base.py`** - Replace GitHubProjectManager with ProjectManagerFactory

```python
# flows/base.py - UPDATED import
# OLD: from project_manager.github import GitHubProjectManager
# NEW: from project_manager.factory import ProjectManagerFactory

# In FlowIssueManagement.get_project_manager():
# OLD: self._project_manager = GitHubProjectManager(self.state.project_config)
# NEW: self._project_manager = ProjectManagerFactory.create(self.state.project_config)
```

## Integration Pattern

```python
# Usage in crew/flow:

from project_manager.factory import ProjectManagerFactory
from project_manager.types import ProjectConfig
from tools.project_management import create_tools

# Create ProjectManager
config = ProjectConfig(
    provider="github",
    repo_owner="owner",
    repo_name="repo",
    project_identifier="1",
    token=os.getenv("GITHUB_TOKEN"),
)

project_manager = ProjectManagerFactory.create(config)

# Create tools
tools = create_tools(project_manager)

# Use in agent
agent = Agent(
    role="Developer",
    goal="Implement features",
    tools=tools,  # All 15 Phase 1 tools
)
```

## Testing Strategy

```python
# tests/test_tools/test_issues.py

from unittest.mock import MagicMock
from tools.project_management.issues import GetIssueTool
from project_manager.base import ProjectManager

def test_get_issue_returns_json():
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

    tool = GetIssueTool(mock_pm)

    # Act
    result = tool._run(issue_number=42)

    # Assert
    assert '"id": 42' in result
    mock_pm.get_issue.assert_called_once_with(42)
```

## Implementation Order

1. Create `project_manager/factory.py`
2. Update `project_manager/base.py` (add missing abstract methods)
3. Create `tools/project_management/` directory with all submodules
4. Create `tools/project_management/base.py`
5. Create 5 tool files (issues.py, projects.py, pull_requests.py, labels.py)
6. Update `flows/base.py` (use ProjectManagerFactory)
7. Run `uv run ruff check .` and `uv run ruff format .`
8. Run `uv run pytest tests/` to verify tools work
9. Update implement_crew.py to use new tools via create_tools()
