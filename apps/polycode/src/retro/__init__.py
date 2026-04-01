"""Retrospective module for continuous improvement.

Provides:
- LLM-powered retrospective generation via CrewAI
- Git-notes storage for transportability
- Pattern analysis for identifying recurring issues
"""

from gitcore import GitNotes, GitNotesError

from .analyzer import PatternAnalyzer
from .types import RetroEntry, RetroQuery

__all__ = [
    "RetroEntry",
    "RetroQuery",
    "GitNotes",
    "GitNotesError",
    "PatternAnalyzer",
]
