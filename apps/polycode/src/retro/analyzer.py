"""Retro pattern analysis — reads from git-notes, not postgres."""

import logging
from collections import Counter
from pathlib import Path
from typing import Any

from gitcore import GitNotes
from gitcore.types import GitContext

from .types import RetroEntry, RetroQuery

logger = logging.getLogger(__name__)

RETRO_NOTES_REF = "refs/notes/retros"


class PatternAnalyzer:
    """Analyze retrospectives stored as git-notes."""

    def __init__(
        self,
        repo_path: str | Path,
        notes_ref: str = RETRO_NOTES_REF,
    ) -> None:
        context = GitContext(repo_path=str(repo_path))
        self.notes = GitNotes(context, notes_ref=notes_ref)

    def _load_retros(self, limit: int = 50) -> list[RetroEntry]:
        """Load recent retro entries from git-notes."""
        commit_shas = self.notes.list_all()
        retros: list[RetroEntry] = []

        for sha in commit_shas:
            if len(retros) >= limit:
                break
            entry = self.notes.show(RetroEntry, commit_sha=sha)
            if entry is not None:
                retros.append(entry)

        retros.sort(key=lambda r: r.timestamp, reverse=True)
        return retros

    def _load_retros_filtered(
        self,
        query: RetroQuery,
    ) -> list[RetroEntry]:
        retros = self._load_retros(limit=query.limit)
        filtered = retros

        if query.repo_owner:
            filtered = [r for r in filtered if r.repo_owner == query.repo_owner]
        if query.repo_name:
            filtered = [r for r in filtered if r.repo_name == query.repo_name]
        if query.retro_type:
            filtered = [r for r in filtered if r.retro_type == query.retro_type]
        if query.since:
            filtered = [r for r in filtered if r.timestamp >= query.since]

        return filtered[: query.limit]

    def analyze_recent_trends(self, limit: int = 20) -> dict[str, Any]:
        retros = self._load_retros(limit=limit)

        trends = {
            "common_failures": self._extract_common_failures(retros),
            "success_factors": self._extract_success_factors(retros),
            "performance_trends": self._analyze_performance_trends(retros),
            "build_patterns": self._analyze_build_patterns(retros),
        }

        logger.info(f"📊 Analyzed {len(retros)} retros for trends")
        return trends

    def _extract_common_failures(self, retros: list[RetroEntry]) -> list[str]:
        all_failures: list[str] = []
        for retro in retros:
            all_failures.extend(retro.what_failed)

        counter = Counter(all_failures)
        top_failures = [item for item, count in counter.most_common(5)]

        logger.info(f"🔴 Top failures: {[f[:40] for f in top_failures]}")
        return top_failures

    def _extract_success_factors(self, retros: list[RetroEntry]) -> list[str]:
        success_retros = [r for r in retros if r.retro_type == "success"]

        all_successes: list[str] = []
        for retro in success_retros:
            all_successes.extend(retro.what_worked)

        counter = Counter(all_successes)
        top_successes = [item for item, count in counter.most_common(5)]

        logger.info(f"🟢 Top success factors: {[s[:40] for s in top_successes]}")
        return top_successes

    def _analyze_performance_trends(self, retros: list[RetroEntry]) -> dict[str, Any]:
        with_duration = [r for r in retros if r.time_to_completion_seconds]

        if not with_duration:
            return {"message": "No duration data available"}

        durations = [r.time_to_completion_seconds for r in with_duration if r.time_to_completion_seconds]
        # type: ignore[union-attr]
        avg_duration = sum(durations) / len(durations)

        with_retries = [r for r in retros if r.retry_count > 0]
        avg_retries = sum(r.retry_count for r in with_retries) / len(with_retries) if with_retries else 0

        # type: ignore[union-attr]

        trends = {
            "avg_duration_seconds": avg_duration,
            "max_duration_seconds": max(durations),
            "min_duration_seconds": min(durations),
            "avg_retries": avg_retries,
            "total_analyzed": len(retros),
        }

        logger.info(f"⏱️ Avg duration: {avg_duration:.1f}s, Avg retries: {avg_retries:.1f}")
        # type: ignore[union-attr]
        return trends

    def _analyze_build_patterns(self, retros: list[RetroEntry]) -> dict[str, Any]:
        failed_builds = [r for r in retros if r.retro_type == "failure"]
        success_builds = [r for r in retros if r.retro_type == "success"]

        with_build_times = [r for r in retros if r.build_duration_ms]

        patterns: dict[str, Any] = {
            "total_failures": len(failed_builds),
            "total_successes": len(success_builds),
            "failure_rate": (len(failed_builds) / len(retros) if retros else 0),
        }

        if with_build_times:
            build_times = [r.build_duration_ms for r in with_build_times if r.build_duration_ms]  # type: ignore[union-attr]
            patterns["avg_build_ms"] = sum(build_times) / len(build_times)
            patterns["max_build_ms"] = max(build_times)
            patterns["min_build_ms"] = min(build_times)

        logger.info(f"🔨 Failure rate: {patterns['failure_rate']:.1%}")
        return patterns

    def generate_context_injection(
        self,
        repo_owner: str = "",
        repo_name: str = "",
        limit: int = 5,
    ) -> str:
        """Generate context for next flow based on past retros."""
        query = RetroQuery(
            repo_owner=repo_owner,
            repo_name=repo_name,
            limit=limit,
        )
        retros = self._load_retros_filtered(query)

        if not retros:
            return ""

        recent_failures = [r for r in retros if r.retro_type == "failure"]
        top_issues = self._get_top_issues(retros)

        context = [
            f"## Previous Retrospectives ({len(retros)} total)",
            "",
            "### Recent Failures",
        ]

        for r in recent_failures[:3]:
            context.append(f"- **Commit {r.commit_sha[:8]}**: {r.retro_type}")
            if r.what_failed:
                context.append(f"  Failed: {r.what_failed[0][:60]}...")

        if top_issues:
            context.extend(["", "### Recurring Issues"])
            for issue, count in top_issues.items():
                context.append(f"- {issue} ({count}x)")

        return "\n".join(context)

    def _get_top_issues(self, retros: list[RetroEntry], limit: int = 3) -> dict[str, int]:
        all_failures: list[str] = []
        for retro in retros:
            all_failures.extend(retro.what_failed)
            all_failures.extend(retro.root_causes)

        counter = Counter(all_failures)
        return dict(counter.most_common(limit))

    def suggest_improvements_from_patterns(self, limit: int = 10) -> list[str]:
        """Suggest improvements based on historical patterns."""
        trends = self.analyze_recent_trends(limit)
        suggestions: list[str] = []

        if trends["common_failures"]:
            suggestions.append("Implement automated testing for common failure paths")
            suggestions.append("Add pre-commit hooks to catch integration issues")

        if trends["performance_trends"]:
            perf = trends["performance_trends"]
            if isinstance(perf, dict) and perf.get("avg_retries", 0) > 2:
                suggestions.append("Reduce retry rate by improving test stability")
            if isinstance(perf, dict) and perf.get("avg_duration_seconds", 0) > 600:
                suggestions.append("Optimize build pipeline for faster feedback loops")

        if trends["build_patterns"]:
            build = trends["build_patterns"]
            if isinstance(build, dict) and build.get("failure_rate", 0) > 0.3:
                suggestions.append("Improve build reliability (30%+ failure rate detected)")

        logger.info(f"💡 Generated {len(suggestions)} improvement suggestions")
        return suggestions
