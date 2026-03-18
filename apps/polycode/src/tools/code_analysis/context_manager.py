"""Context manager for code analysis tools.

Provides shared state for tree-sitter and LSP tools including project root,
parser registry, and language detection.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path

from tree_sitter import Language, Parser

from tools.code_analysis.language_support import (
    EXTENSION_MAP,
    LanguageSupport,
    get_language_support,
)

log = logging.getLogger(__name__)


@dataclass
class CodeContext:
    """Shared state for code analysis tools.

    Manages project root, parser instances, and language detection.
    """

    project_root: Path
    language_support: LanguageSupport = field(default_factory=get_language_support)
    _parsers: dict[str, Parser] = field(default_factory=dict)
    _language_cache: dict[str, Language] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Ensure project_root is a Path object."""
        if isinstance(self.project_root, str):
            self.project_root = Path(self.project_root)
        self.project_root = self.project_root.resolve()

    def detect_language(self, file_path: Path | str) -> str | None:
        """Detect language from file extension.

        Args:
            file_path: Path to the file

        Returns:
            Language name or None if unknown
        """
        file_path = Path(file_path)
        ext = file_path.suffix.lower()
        return EXTENSION_MAP.get(ext)

    def get_parser(self, language: str) -> Parser | None:
        """Get or create a parser for a language.

        Args:
            language: Language name (e.g., 'python', 'typescript')

        Returns:
            Parser instance or None if language not available
        """
        if language in self._parsers:
            return self._parsers[language]

        parser = self.language_support.get_parser(language)
        if parser:
            self._parsers[language] = parser
        return parser

    def get_language(self, language: str) -> Language | None:
        """Get the Language object for a language.

        Args:
            language: Language name

        Returns:
            Language object or None if not available
        """
        if language in self._language_cache:
            return self._language_cache[language]

        lang = self.language_support.get_language(language)
        if lang:
            self._language_cache[language] = lang
        return lang

    def resolve_import_path(self, import_name: str, from_file: Path | str) -> Path | None:
        """Resolve an import to a local file path.

        Args:
            import_name: The import module name (e.g., 'tools.code_analysis.types')
            from_file: The file containing the import

        Returns:
            Resolved file path or None if not found
        """
        from_file = Path(from_file)
        if not from_file.is_absolute():
            from_file = self.project_root / from_file

        # Try relative to the importing file's directory
        import_parts = import_name.replace(".", "/")
        base_dir = from_file.parent

        # Try various extensions
        extensions = [".py", ".ts", ".tsx", ".js", ".go", ".rs"]

        # Try as a direct file
        for ext in extensions:
            candidate = base_dir / f"{import_parts}{ext}"
            if candidate.exists():
                return candidate

        # Try as a package (index file)
        for index_file in ["__init__.py", "index.ts", "index.js"]:
            candidate = base_dir / import_parts / index_file
            if candidate.exists():
                return candidate

        # Try from project root
        for ext in extensions:
            candidate = self.project_root / f"{import_parts}{ext}"
            if candidate.exists():
                return candidate

        for index_file in ["__init__.py", "index.ts", "index.js"]:
            candidate = self.project_root / import_parts / index_file
            if candidate.exists():
                return candidate

        return None

    def is_language_supported(self, language: str) -> bool:
        """Check if a language is supported.

        Args:
            language: Language name

        Returns:
            True if language is available
        """
        return self.language_support.is_language_available(language)

    def get_supported_languages(self) -> list[str]:
        """Get list of supported languages.

        Returns:
            List of available language names
        """
        return self.language_support.get_available_languages()
