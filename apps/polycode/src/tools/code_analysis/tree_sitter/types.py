"""Pydantic models for code analysis tool outputs."""

from enum import Enum

from pydantic import BaseModel, Field


class SymbolKind(str, Enum):
    """Kind of code symbol."""

    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    VARIABLE = "variable"
    CONSTANT = "constant"
    IMPORT = "import"
    TYPE_ALIAS = "type_alias"
    INTERFACE = "interface"
    MODULE = "module"
    PROPERTY = "property"


class Position(BaseModel):
    """Position in a file."""

    line: int = Field(..., description="Line number (1-indexed)")
    column: int = Field(..., description="Column number (0-indexed)")


class Range(BaseModel):
    """Range in a file."""

    start: Position = Field(..., description="Start position")
    end: Position = Field(..., description="End position")


class Symbol(BaseModel):
    """A code symbol with metadata."""

    name: str = Field(..., description="Symbol name")
    kind: SymbolKind = Field(..., description="Symbol kind")
    range: Range = Field(..., description="Position range in file")
    signature: str | None = Field(default=None, description="Full signature (for functions/methods)")
    docstring: str | None = Field(default=None, description="Docstring or comment")
    parent: str | None = Field(default=None, description="Parent symbol name (for nested symbols)")


class Import(BaseModel):
    """An import statement."""

    module_path: str = Field(..., description="Imported module path")
    imported_names: list[str] = Field(default_factory=list, description="Names imported from module")
    range: Range = Field(..., description="Position in file")
    is_relative: bool = Field(default=False, description="Whether import is relative")
    alias: str | None = Field(default=None, description="Alias for imported module")
    resolved_path: str | None = Field(default=None, description="Resolved local file path")


class FileSkeleton(BaseModel):
    """Skeleton of a file - signatures without bodies."""

    file_path: str = Field(..., description="Path to the file")
    language: str = Field(..., description="Detected language")
    symbols: list[Symbol] = Field(default_factory=list, description="Symbols found in file")
    imports: list[Import] = Field(default_factory=list, description="Imports in file")
    total_lines: int = Field(..., description="Total lines in file")


class SymbolUsage(BaseModel):
    """A usage/reference of a symbol."""

    file_path: str = Field(..., description="File containing the usage")
    range: Range = Field(..., description="Position of the usage")
    context: str | None = Field(default=None, description="Surrounding code context")
    kind: str = Field(default="reference", description="Kind of usage (reference, definition, import)")


class BlastRadius(BaseModel):
    """All usages of a symbol across the project."""

    symbol_name: str = Field(..., description="Symbol name searched")
    definition: SymbolUsage | None = Field(default=None, description="Where symbol is defined")
    usages: list[SymbolUsage] = Field(default_factory=list, description="All usages of the symbol")
    total_count: int = Field(..., description="Total number of usages")


class HoverInfo(BaseModel):
    """Hover information from LSP."""

    file_path: str = Field(..., description="File path")
    position: Position = Field(..., description="Position queried")
    type_info: str | None = Field(default=None, description="Type signature")
    documentation: str | None = Field(default=None, description="Documentation string")
    signature: str | None = Field(default=None, description="Full signature")


class Definition(BaseModel):
    """Definition location from LSP."""

    file_path: str = Field(..., description="File containing definition")
    range: Range = Field(..., description="Range of definition")
    preview: str | None = Field(default=None, description="Preview of definition")


class Reference(BaseModel):
    """A reference from LSP."""

    file_path: str = Field(..., description="File containing reference")
    range: Range = Field(..., description="Range of reference")
    preview: str | None = Field(default=None, description="Preview of reference")


class Diagnostic(BaseModel):
    """A diagnostic from LSP."""

    file_path: str = Field(..., description="File with diagnostic")
    range: Range = Field(..., description="Range of diagnostic")
    severity: str = Field(..., description="Severity: error, warning, info, hint")
    message: str = Field(..., description="Diagnostic message")
    source: str | None = Field(default=None, description="Source linter/tool")
    code: str | None = Field(default=None, description="Error code")
    suggested_fixes: list[dict[str, str]] = Field(default_factory=list, description="Suggested fixes")


class DiagnosticsResult(BaseModel):
    """Result of getting diagnostics."""

    file_path: str = Field(..., description="File path")
    diagnostics: list[Diagnostic] = Field(default_factory=list, description="Diagnostics found")
    error_count: int = Field(..., description="Number of errors")
    warning_count: int = Field(..., description="Number of warnings")
