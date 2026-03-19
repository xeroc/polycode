"""Retro pattern analysis and improvement suggestions."""

import logging
from collections import Counter

from .persistence import RetroStore
from .types import RetroEntry, RetroQuery

logger = logging.getLogger(__name__)


class PatternAnalyzer:
    """Analyze retrospectives to identify recurring patterns and trends."""

    def __init__(self, store: RetroStore) -> None:
        """Initialize pattern analyzer.

        Args:
            store: RetroStore instance for querying retros
        """
        self.store = store

    def analyze_recent_trends(self, limit: int = 20) -> dict[str, list[str]]:
        """Analyze recent retros for emerging patterns.

        Args:
            limit: Number of recent retros to analyze

        Returns:
            Dict with categories and their patterns
        """
        params = RetroQuery(limit=limit)
        retros = self.store.query(params)

        trends = {
            "common_failures": self._extract_common_failures(retros),
            "success_factors": self._extract_success_factors(retros),
            "performance_trends": self._analyze_performance_trends(retros),
            "build_patterns": self._analyze_build_patterns(retros),
        }

        logger.info(f"📊 Analyzed {len(retros)} retros for trends")
        return trends

    def _extract_common_failures(self, retros: list[RetroEntry]) -> list[str]:
        """Extract most common failure patterns.

        Args:
            retros: List of retrospectives

        Returns:
            List of common failure descriptions
        """
        all_failures: list[str] = []
        for retro in retros:
            all_failures.extend(retro.what_failed)

        counter = Counter(all_failures)
        top_failures = [item for item, count in counter.most_common(5)]

        logger.info(f"🔴 Top failures: {[f[:40] for f in top_failures]}")
        return top_failures

    def _extract_success_factors(self, retros: list[RetroEntry]) -> list[str]:
        """Extract factors that correlate with success.

        Args:
            retros: List of retrospectives

        Returns:
            List of success patterns
        """
        success_retros = [r for r in retros if r.retro_type == "success"]

        all_successes: list[str] = []
        for retro in success_retros:
            all_successes.extend(retro.what_worked)

        counter = Counter(all_successes)
        top_successes = [item for item, count in counter.most_common(5)]

        logger.info(f"🟢 Top success factors: {[s[:40] for s in top_successes]}")
        return top_successes

    def _analyze_performance_trends(self, retros: list[RetroEntry]) -> dict:
        """Analyze performance metrics over time.

        Args:
            retros: List of retrospectives

        Returns:
            Dict with performance metrics
        """
        with_duration = [r for r in retros if r.time_to_completion_seconds]

        if not with_duration:
            return {"message": "No duration data available"}

        durations = [r.time_to_completion_seconds for r in with_duration if r.time_to_completion_seconds]
        avg_duration = sum(durations) / len(durations)

        with_retries = [r for r in retros if r.retry_count > 0]
        avg_retries = sum(r.retry_count for r in with_retries) / len(with_retries) if with_retries else 0

        trends = {
            "avg_duration_seconds": avg_duration,
            "max_duration_seconds": max(durations),
            "min_duration_seconds": min(durations),
            "avg_retries": avg_retries,
            "total_analyzed": len(retros),
        }

        logger.info(f"⏱️ Avg duration: {avg_duration:.1f}s, Avg retries: {avg_retries:.1f}")
        return trends

    def _analyze_build_patterns(self, retros: list[RetroEntry]) -> dict:
        """Analyze build success/failure patterns.

        Args:
            retros: List of retrospectives

        Returns:
            Dict with build statistics
        """
        failed_builds = [r for r in retros if r.retro_type == "failure"]
        success_builds = [r for r in retros if r.retro_type == "success"]

        with_build_times = [r for r in retros if r.build_duration_ms]

        patterns = {
            "total_failures": len(failed_builds),
            "total_successes": len(success_builds),
            "failure_rate": (len(failed_builds) / len(retros) if retros else 0),
        }

        if with_build_times:
            build_times = [r.build_duration_ms for r in with_build_times if r.build_duration_ms]
            patterns["avg_build_ms"] = sum(build_times) / len(build_times)
            patterns["max_build_ms"] = max(build_times)
            patterns["min_build_ms"] = min(build_times)

        logger.info(f"🔨 Failure rate: {patterns['failure_rate']:.1%}")
        return patterns

    def generate_context_injection(self, repo_owner: str, repo_name: str, limit: int = 5) -> str:
        """Generate context for next flow based on past retros.

        Args:
            repo_owner: Repository owner
            repo_name: Repository name
            limit: Number of recent retros to include

        Returns:
            Markdown formatted context string
        """
        params = RetroQuery(
            repo_owner=repo_owner,
            repo_name=repo_name,
            limit=limit,
        )
        retros = self.store.query(params)

        if not retros:
            return "No previous retros for this repository."

        recent_failures = [r for r in retros if r.retro_type == "failure"]
        top_issues = self.store.get_top_issues(limit=3)

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

    def suggest_improvements_from_patterns(self, limit: int = 10) -> list[str]:
        """Suggest improvements based on historical patterns.

        Args:
            limit: Number of recent retros to analyze

        Returns:
            List of improvement suggestions
        """
        trends = self.analyze_recent_trends(limit)
        suggestions = []

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
