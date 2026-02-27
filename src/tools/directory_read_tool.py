import os
from pathlib import Path
from typing import Any

from crewai.tools import BaseTool
from pathspec import PathSpec
from pathspec.patterns.gitwildmatch import GitWildMatchPattern
from pydantic import BaseModel, Field


class FixedDirectoryReadToolSchema(BaseModel):
    """Input for DirectoryReadTool."""


class DirectoryReadToolSchema(FixedDirectoryReadToolSchema):
    """Input for DirectoryReadTool."""

    directory: str = Field(..., description="Mandatory directory to list content")


class DirectoryReadTool(BaseTool):
    name: str = "List files in directory"
    description: str = (
        "A tool that can be used to recursively list a directory's content."
    )
    args_schema: type[BaseModel] = DirectoryReadToolSchema
    directory: str | None = None

    def __init__(self, directory: str | None = None, **kwargs):
        super().__init__(**kwargs)
        if directory is not None:
            self.directory = directory
            self.description = f"A tool that can be used to list {directory}'s content."
            self.args_schema = FixedDirectoryReadToolSchema
            self._generate_description()

    def _load_ignore_patterns(self, base_path: Path) -> PathSpec:
        """Load and parse ignore patterns from .gitignore and .dockerignore."""
        patterns = [".*"]

        ignore_files = [base_path / ".gitignore", base_path / ".dockerignore"]
        for ignore_file in ignore_files:
            if ignore_file.exists():
                with open(ignore_file) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            patterns.append(line)

        return PathSpec.from_lines(GitWildMatchPattern, patterns)

    def _is_ignored(self, path: Path, base_path: Path, spec: PathSpec) -> bool:
        """Check if a path matches ignore patterns."""
        relative_path = str(path.relative_to(base_path))
        if spec.match_file(relative_path):
            return True

        for parent in path.parents:
            if parent == base_path:
                break
            if parent.name.startswith("."):
                return True

        return False

    def _run(
        self,
        **kwargs: Any,
    ) -> Any:
        directory: str | None = kwargs.get("directory", self.directory)
        if directory is None:
            raise ValueError("Directory must be provided.")

        base_path = Path(directory)
        spec = self._load_ignore_patterns(base_path)

        files_list = []
        for file_path in base_path.rglob("*"):
            if not file_path.is_file():
                continue

            if self._is_ignored(file_path, base_path, spec):
                continue

            relative_path = file_path.relative_to(base_path)
            files_list.append(str(relative_path))

        files = "\n- ".join(sorted(files_list))
        return f"File paths:\n- {files}"
