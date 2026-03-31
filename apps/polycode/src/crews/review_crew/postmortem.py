"""Postmortem hook — Night Shift failure analysis.

When a flow fails, analyze the error and suggest doc/workflow improvements.
This is the Night Shift pattern: fix docs FIRST, then fix code.
"""

import logging

from modules.hooks import FlowEvent, hookimpl

log = logging.getLogger(__name__)


class PostmortemHooks:
    """Hook implementation for postmortem failure analysis."""

    @hookimpl
    def on_flow_event(self, event, flow_id, state, result, label) -> None:
        """Handle FLOW_ERROR events with postmortem analysis.

        Night Shift pattern: don't just fix code — fix the docs/workflow
        that led to the wrong decision.
        """
        if event != FlowEvent.FLOW_ERROR:
            return

        try:
            from crews.review_crew.review_crew import ReviewCrew

            crew = ReviewCrew()
            improvements = crew.apply_doc_improvements(  # type: ignore[union-attr]
                error_context=str(result),
                flow_id=flow_id,
                label=label or "unknown",
            )

            if improvements:
                log.warning(
                    f"📋 Postmortem doc improvements "
                    f"(flow={flow_id}, label={label}):\n" + "\n".join(f"  - {imp}" for imp in improvements)
                )
            else:
                log.info(f"📋 Postmortem: no doc improvements needed for flow {flow_id}")
        except Exception as e:
            log.error(f"🚨 Postmortem analysis failed for flow {flow_id}: {e}")
