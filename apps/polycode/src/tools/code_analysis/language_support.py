"""Language detection and parser factory for tree-sitter."""

import logging
from pathlib import Path

from tree_sitter import Language, Parser

log = logging.getLogger(__name__)

LANGUAGE_MAP: dict[str, tuple[str, str]] = {
    "python": (".py", "Python"),
    "javascript": (".js", "JavaScript"),
    "jsx": (".jsx", "JavaScript (JSX)"),
    "typescript": (".ts", "TypeScript"),
    "tsx": (".tsx", "TypeScript (TSX)"),
    "go": (".go", "Go"),
    "rust": (".rs", "Rust"),
}

EXTENSION_MAP: dict[str, str] = {
    ".py": "python",
    ".pyi": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".go": "go",
    ".rs": "rust",
}


class LanguageSupport:
    """Manages tree-sitter language parsers."""

    _parsers: dict[str, Parser]
    _languages: dict[str, Language | None]
    _available: dict[str, bool]

    def __init__(self) -> None:
        self._parsers = {}
        self._languages = {}
        self._available = {}
        self._detect_available_languages()

    def _detect_available_languages(self) -> None:
        """Check which language grammars are installed."""
        language_packages = [
            ("python", "tree_sitter_python"),
            ("javascript", "tree_sitter_javascript"),
            ("typescript", "tree_sitter_typescript"),
            ("go", "tree_sitter_go"),
            ("rust", "tree_sitter_rust"),
        ]

        for lang_name, package_name in language_packages:
            try:
                __import__(package_name)
                self._available[lang_name] = True
                log.debug(f"✓ {lang_name} grammar available")
            except ImportError:
                self._available[lang_name] = False
                log.debug(f"✗ {lang_name} grammar not available")

    def is_language_available(self, language: str) -> bool:
        """Check if a language is available."""
        return self._available.get(language, False)

    def get_available_languages(self) -> list[str]:
        """Get list of available languages."""
        return [lang for lang, avail in self._available.items() if avail]

    def detect_language(self, file_path: Path | str) -> str | None:
        """Detect language from file extension."""
        file_path = Path(file_path)
        ext = file_path.suffix.lower()
        return EXTENSION_MAP.get(ext)

    def get_parser(self, language: str) -> Parser | None:
        """Get or create a parser for a language."""
        if language in self._parsers:
            return self._parsers[language]

        if not self.is_language_available(language):
            log.warning(f"Language {language} not available")
            return None

        parser = self._create_parser(language)
        if parser:
            self._parsers[language] = parser
        return parser

    def _create_parser(self, language: str) -> Parser | None:
        """Create a new parser for the given language."""
        try:
            parser = Parser()

            if language == "python":
                import tree_sitter_python

                parser.language = Language(tree_sitter_python.language())
            elif language == "javascript":
                import tree_sitter_javascript

                parser.language = Language(tree_sitter_javascript.language())
            elif language in ("typescript", "tsx"):
                import tree_sitter_typescript

                if language == "tsx":
                    parser.language = Language(tree_sitter_typescript.language_tsx())
                else:
                    parser.language = Language(tree_sitter_typescript.language_typescript())
            elif language == "go":
                import tree_sitter_go

                parser.language = Language(tree_sitter_go.language())
            elif language == "rust":
                import tree_sitter_rust

                parser.language = Language(tree_sitter_rust.language())
            else:
                log.warning(f"Unknown language: {language}")
                return None

            log.info(f"🏹 Created parser for {language}")
            return parser

        except Exception as e:
            log.error(f"🚨 Failed to create parser for {language}: {e}")
            return None

    def get_language(self, language: str) -> Language | None:
        """Get Language object for a language."""
        if language in self._languages:
            return self._languages[language]

        parser = self.get_parser(language)
        if parser:
            lang = parser.language
            self._languages[language] = lang
            return lang
        return None


_language_support: LanguageSupport | None = None


def get_language_support() -> LanguageSupport:
    """Get the singleton language support instance."""
    global _language_support
    if _language_support is None:
        _language_support = LanguageSupport()
    return _language_support
