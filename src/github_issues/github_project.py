"""GitHub Projects V2 GraphQL API client with full type annotations."""

import logging

import httpx
from pydantic import BaseModel

log = logging.getLogger(__name__)


class GraphQLResponse(BaseModel):
    """Generic GraphQL response structure."""

    data: dict


class StatusFieldOption(BaseModel):
    """Status option with ID and name."""

    id: str
    name: str


class StatusFieldData(BaseModel):
    """Status field with ID and options."""

    id: str
    options: list[StatusFieldOption]


class ProjectItemContent(BaseModel):
    """Issue content in a project item."""

    number: int
    title: str
    body: str | None


class ProjectItemStatus(BaseModel):
    """Status field value for a project item."""

    name: str


class ProjectItem(BaseModel):
    """Item in a GitHub project."""

    project_item_id: str
    issue_number: int
    title: str
    body: str | None
    status: str | None

    class Config:
        """Pydantic config for field aliases."""

        populate_by_name = True


class GitHubProjectsClient:
    """Client for GitHub Projects V2 GraphQL API."""

    def __init__(self, token: str, repo_name: str) -> None:
        """Initialize the GitHub Projects client.

        Args:
            token: GitHub personal access token.
            repo_name: Name of the repository.
        """
        self.repo_name = repo_name
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        self.endpoint = "https://api.github.com/graphql"

    def _query(
        self, query: str, variables: dict | None = None
    ) -> GraphQLResponse:
        """Execute a GraphQL query.

        Args:
            query: GraphQL query string.
            variables: Optional variables for the query.

        Returns:
            GraphQL response with data.

        Raises:
            httpx.HTTPStatusError: If the request fails.
        """
        with httpx.Client() as client:
            response = client.post(
                self.endpoint,
                headers=self.headers,
                json={"query": query, "variables": variables or {}},
                timeout=30,
            )
            response.raise_for_status()
            return GraphQLResponse(**response.json())

    def get_project_id(self, owner: str, project_number: int) -> str:
        """Get the global ID for a project.

        Args:
            owner: Repository owner.
            project_number: Project number.

        Returns:
            Global ID of the project.
        """
        query = (
            """
        query($owner: String!, $projectNumber: Int!) {
            repository(owner: $owner, name: "%s") {
                projectV2(number: $projectNumber) {
                    id
                }
            }
        }
        """
            % self.repo_name
        )
        result = self._query(
            query, {"owner": owner, "projectNumber": project_number}
        )
        return result.data["repository"]["projectV2"]["id"]

    def get_project_items(self, project_id: str) -> list[ProjectItem]:
        """Get all items in a project with their status.

        Args:
            project_id: Global ID of the project.

        Returns:
            List of project items with issue data and status.
        """
        query = """
        query($projectId: ID!, $cursor: String) {
            node(id: $projectId) {
                ... on ProjectV2 {
                    items(first: 100, after: $cursor) {
                        pageInfo {
                            hasNextPage
                            endCursor
                        }
                        nodes {
                            id
                            content {
                                ... on Issue {
                                    number
                                    title
                                    body
                                }
                            }
                            fieldValueByName(name: "Status") {
                                ... on ProjectV2ItemFieldSingleSelectValue {
                                    name
                                }
                            }
                        }
                    }
                }
            }
        }
        """
        items: list[ProjectItem] = []
        cursor: str | None = None
        while True:
            result = self._query(
                query, {"projectId": project_id, "cursor": cursor}
            )
            data = result.data["node"]["items"]
            for node in data["nodes"]:
                content = node.get("content")
                if content:
                    status_field = node.get("fieldValueByName")
                    items.append(
                        ProjectItem(
                            project_item_id=node["id"],
                            issue_number=content["number"],
                            title=content["title"],
                            body=content["body"],
                            status=status_field["name"]
                            if status_field
                            else None,
                        )
                    )
            if not data["pageInfo"]["hasNextPage"]:
                break
            cursor = data["pageInfo"]["endCursor"]
        return items

    def add_issue_to_project(
        self, project_id: str, issue_node_id: str
    ) -> str | None:
        """Add an issue to a project.

        Args:
            project_id: Global ID of the project.
            issue_node_id: Global ID of the issue to add.

        Returns:
            Project item ID if successful, None otherwise.
        """
        query = """
        mutation($projectId: ID!, $contentId: ID!) {
            addProjectV2ItemById(input: {projectId: $projectId, contentId: $contentId}) {
                item {
                    id
                }
            }
        }
        """
        result = self._query(
            query, {"projectId": project_id, "contentId": issue_node_id}
        )
        return result.data["addProjectV2ItemById"]["item"]["id"]

    def get_status_field_id(
        self, project_id: str
    ) -> tuple[str, dict[str, str]]:
        """Get the ID and options of the Status field in a project.

        Args:
            project_id: Global ID of the project.

        Returns:
            Tuple of (field_id, dict mapping status names to option IDs).
        """
        query = """
        query($projectId: ID!) {
            node(id: $projectId) {
                ... on ProjectV2 {
                    field(name: "Status") {
                        ... on ProjectV2SingleSelectField {
                            id
                            options {
                                id
                                name
                            }
                        }
                    }
                }
            }
        }
        """
        result = self._query(query, {"projectId": project_id})
        field = result.data["node"]["field"]
        options = {opt["name"]: opt["id"] for opt in field["options"]}
        return field["id"], options

    def update_item_status(
        self,
        project_id: str,
        item_id: str,
        field_id: str,
        option_id: str,
    ) -> bool:
        """Update the status of a project item.

        Args:
            project_id: Global ID of the project.
            item_id: ID of the project item.
            field_id: ID of the status field.
            option_id: ID of the status option to set.

        Returns:
            True if successful, False otherwise.
        """
        query = """
        mutation($projectId: ID!, $itemId: ID!, $fieldId: ID!, $optionId: String!) {
            updateProjectV2ItemFieldValue(input: {
                projectId: $projectId,
                itemId: $itemId,
                fieldId: $fieldId,
                value: { singleSelectOptionId: $optionId }
            }) {
                projectV2Item {
                    id
                }
            }
        }
        """
        result = self._query(
            query,
            {
                "projectId": project_id,
                "itemId": item_id,
                "fieldId": field_id,
                "optionId": option_id,
            },
        )
        return "updateProjectV2ItemFieldValue" in result.data
