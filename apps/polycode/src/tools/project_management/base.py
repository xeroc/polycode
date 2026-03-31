"""Base class for all project management MCP tools."""

from crewai.tools import BaseTool

from project_manager.base import ProjectManager


class ProjectManagementToolBase(BaseTool):
    """Concrete base class for all project management MCP tools.

    Subclasses implement _run() with operation-specific logic.
    Common initialization (ProjectManager injection) happens in __init__.
    """

    _pm: ProjectManager

    def __init__(self, project_manager: ProjectManager, **kwargs):
        """Initialize tool with ProjectManager instance.

        Args:
            project_manager: ProjectManager instance (GitHub, Jira, GitLab, etc.)
        """
        super().__init__(**kwargs)
        self._pm = project_manager
