"""Base classes for tree-sitter tools."""

import logging
from pathlib import Path
from typing import Any

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from tree_sitter import Parser

from tools.code_analysis.language_support import (
    LanguageSupport,
    get_language_support,
)
from tools.code_analysis.tree_sitter.types import Position, Range

log = logging.getLogger(__name__)


class TreeSitterToolInput(BaseModel):
    """Base input schema for tree-sitter tools."""

    file_path: str = Field(..., description="Path to file (relative to project root)")


class BaseTreeSitterTool(BaseTool):
    """Base class for tree-sitter based code analysis tools.

    Provides common functionality for parsing files and extracting node information.
    """

    project_root: Path
    language_support: LanguageSupport
    max_file_size: int = 100000
    _parsers: dict[str, Parser] = {}
    _ast_cache: dict[str, Any] = {}

    def __init__(
        self,
        project_root: str | Path | None = None,
        language_support: LanguageSupport | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.project_root = Path(project_root).resolve() if project_root else Path.cwd()
        self.language_support = language_support or get_language_support()
        self._parsers = {}
        self._ast_cache = {}

    def _resolve_path(self, file_path: str) -> Path:
        """Resolve file path relative to project root."""
        path = Path(file_path)
        if path.is_absolute():
            return path
        return self.project_root / file_path

    def _load_file(self, file_path: Path) -> tuple[bytes | None, str | None]:
        """Load file content.

        Returns:
            Tuple of (content, error_message). If successful, error_message is None.
        """
        try:
            if not file_path.exists():
                return None, f"File not found: {file_path}"

            if not file_path.is_file():
                return None, f"Not a file: {file_path}"

            with open(file_path, "rb") as f:
                content = f.read()

            if len(content) > self.max_file_size:
                log.warning(f"📄 File too large ({file_path}), truncating")
                content = content[: self.max_file_size]

            return content, None

        except PermissionError:
            return None, f"Permission denied: {file_path}"
        except Exception as e:
            log.error(f"🚨 Failed to read file {file_path}: {e}")
            return None, f"Error reading file: {e}"

    def _get_parser(self, language: str) -> Parser | None:
        """Get or create a parser for the given language."""
        if language in self._parsers:
            return self._parsers[language]

        parser = self.language_support.get_parser(language)
        if parser:
            self._parsers[language] = parser
        return parser

    def _parse_file(self, file_path: Path, content: bytes | None = None) -> tuple[Any | None, bytes | None, str | None]:
        """Parse a file and return (tree, source, error).

        Args:
            file_path: Path to file
            content: Optional pre-loaded content

        Returns:
            Tuple of (tree, source_bytes, error_message)
        """
        if content is None:
            content, error = self._load_file(file_path)
            if error:
                return None, None, error

        if content is None:
            return None, None, f"Failed to load file: {file_path}"

        language = self.language_support.detect_language(file_path)
        if not language:
            return None, content, f"Unknown language for file: {file_path}"

        parser = self._get_parser(language)
        if not parser:
            return (
                None,
                content,
                f"Language '{language}' not available. Install tree-sitter-{language}",
            )

        try:
            tree = parser.parse(content)
            return tree, content, None
        except Exception as e:
            log.error(f"🚨 Failed to parse {file_path}: {e}")
            return None, content, f"Parse error: {e}"

    def _get_node_text(self, node: Any, source: bytes) -> str:
        """Get text content of a node."""
        return source[node.start_byte : node.end_byte].decode("utf-8", errors="replace")

    def _node_to_range(self, node: Any) -> Range:
        """Convert a tree-sitter node to a Range model."""
        return Range(
            start=Position(line=node.start_point.row + 1, column=node.start_point.column),
            end=Position(line=node.end_point.row + 1, column=node.end_point.column),
        )

    def _walk_nodes(self, root: Any, node_type: str | None = None) -> list[Any]:
        """Walk the tree and collect nodes of a specific type."""
        nodes = []

        def walk(node):
            if node_type is None or node.type == node_type:
                nodes.append(node)
            for child in node.children:
                walk(child)

        walk(root)
        return nodes

    def _find_nodes_by_query(self, root: Any, source: bytes, query_str: str, language_name: str) -> list[dict]:
        """Find nodes using a tree-sitter query.

        Args:
            root: Root node
            source: Source bytes
            query_str: Tree-sitter query string
            language_name: Language name for query compilation

        Returns:
            List of dicts with 'captures' and 'range' keys
        """
        results = []
        language = self.language_support.get_language(language_name)

        if not language:
            return results

        try:
            query = language.query(query_str)
            for capture in query.captures(root):  # type: ignore[attr-defined]
                node = capture[0]
                capture_name = capture[1]
                results.append(
                    {
                        "capture_name": capture_name,
                        "text": self._get_node_text(node, source),
                        "range": self._node_to_range(node),
                    }
                )
        except Exception as e:
            log.warning(f"Query error: {e}")

        return results
