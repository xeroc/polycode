"""Specify flow for pair-programming-style specification refinement."""

import logging
from datetime import UTC, datetime

from crewai import listen, persist, start

from crews.conversation_crew import ConversationCrew, SpecOutput
from flows.base import FlowIssueManagement, KickoffIssue
from gitcore.operations import sanitize_branch_name
from modules.hooks import FlowEvent
from persistence.postgres import persistence

from .types import SpecifyFlowState, SpecifyStage

logger = logging.getLogger(__name__)

COMPLETION_KEYWORDS = {"lgtm", "lfg", "looks good", "looks good to me", "ship it", "ready"}
MAX_RETRIES = 3


@persist(persistence=persistence, verbose=False)
class SpecifyFlow(FlowIssueManagement[SpecifyFlowState]):
    """Flow for refining specifications via GitHub issue comments."""

    @start()
    def setup(self):
        """Initialize flow and emit FLOW_STARTED event."""
        logger.info("🚀 Ralph Loop starting...")
        self._emit(FlowEvent.FLOW_STARTED, label="ralph")
        self._setup()

    @listen(setup)
    def generate_initial_questions(self, state: SpecifyFlowState) -> SpecifyFlowState:
        """Generate initial clarifying questions from issue."""
        logger.info(f"❓ Generating initial questions for issue #{state.issue_id}")

        result = (
            ConversationCrew()
            .crew()
            .kickoff(
                inputs={
                    "conversation_history": self._format_conversation(state.conversation_history),
                    "current_stage": "initial",
                }
            )
        )

        # Post comment to issue
        comment_body: SpecOutput = result.pydantic  # pyright:ignore
        self._post_comment(state, comment_body)

        state.conversation_history.append({"role": "assistant", "content": comment_body, "source": "flow"})
        state.stage = SpecifyStage.WAITING
        state.updated_at = datetime.now(UTC)

        logger.info("💬 Posted initial questions, waiting for response")

        return state

    @listen("resume")
    def process_new_comments(self, state: SpecifyFlowState) -> SpecifyFlowState:
        """Process new comments from issue author."""
        logger.info(f"📨 Processing new comments for issue #{state.issue_id}")

        # Fetch new comments
        new_comments = self._fetch_new_comments(state)

        if not new_comments:
            logger.info("📭 No new comments, returning to wait state")
            state.stage = SpecifyStage.WAITING
            return state

        # Add comments to history
        for comment in new_comments:
            state.conversation_history.append(
                {"role": "user", "content": comment["body"], "source": "comment", "id": comment["id"]}
            )
            state.last_processed_comment_id = comment["id"]

        # Check for completion keywords
        if comment and self._contains_completion_keyword(comment["body"]):  # pyright:ignore (last comment)
            logger.info(f"✅ Completion keyword detected: {comment['body']}")
            state.specification_complete = True
            state.completion_keyword = comment["body"].strip()
            return state

        # Generate follow-up with ConversationCrew
        state.stage = SpecifyStage.PROCESSING

        try:
            result = (
                ConversationCrew()
                .crew()
                .kickoff(
                    inputs={
                        "conversation_history": self._format_conversation(state.conversation_history),
                        "current_stage": "refinement",
                    }
                )
            )

            # Post response
            comment_body: SpecOutput = result.pydantic  # pyright:ignore
            self._post_comment(state, comment_body)

            state.conversation_history.append({"role": "assistant", "content": comment_body, "source": "flow"})
            state.stage = SpecifyStage.WAITING
            state.updated_at = datetime.now(UTC)

            logger.info("💬 Posted follow-up, waiting for response")

        except Exception as e:
            logger.error(f"🚨 Failed to process comments: {e}")
            state.last_error = str(e)
            state.retry_count += 1

            if state.retry_count >= MAX_RETRIES:
                logger.error("🚨 Max retries exceeded, marking as error")
                state.stage = SpecifyStage.ERROR

        return state

    def _complete_flow(self, state: SpecifyFlowState) -> SpecifyFlowState:
        """Complete flow and produce stories."""
        logger.info(f"🏁 Completing specify flow for issue #{state.issue_id}")

        state.stage = SpecifyStage.COMPLETED
        state.updated_at = datetime.now(UTC)

        # TODO: label the issue with corresponding label for implemenation
        self._add_label(state, "COMPLETED")

        return state

    # Helper methods

    def _format_conversation(self, history: list[dict]) -> str:
        """Format conversation history for crew input."""
        lines = []
        for entry in history:
            role = entry.get("role", "unknown")
            content = entry.get("content", "")
            lines.append(f"[{role.upper()}]: {content}")
        return "\n\n".join(lines)

    def _contains_completion_keyword(self, text: str) -> bool:
        """Check if text contains a completion keyword."""
        text_lower = text.lower().strip()
        return any(kw in text_lower for kw in COMPLETION_KEYWORDS)

    def _post_comment(self, state: SpecifyFlowState, body: SpecOutput) -> None:
        """Post a comment to the issue."""
        # TODO: Implement with GitHubProjectManager
        logger.info(f"📝 Would post comment to #{state.issue_id}: {body.specification[:100]}...")

    def _fetch_new_comments(self, state: SpecifyFlowState) -> list[dict]:
        """Fetch new comments from issue author."""
        # TODO: Implement with GitHubProjectManager
        # Filter by: author == state.issue_author
        # Filter by: id > state.last_processed_comment_id
        return []

    def _add_label(self, state: SpecifyFlowState, label: str) -> None:
        """Add a label to the issue."""
        # TODO: Implement with GitHubProjectManager
        logger.info(f"🏷️ Would add label '{label}' to #{state.issue_id}")

    def _format_stories_summary(self, stories: list) -> str:
        """Format stories for comment."""
        lines = []
        for i, story in enumerate(stories, 1):
            lines.append(f"### {i}. {story.title}")
            lines.append(f"{story.description}")
            lines.append("")
        return "\n".join(lines)


def kickoff(issue: KickoffIssue):
    """Run Ralph Loop with event-driven architecture.

    Args:
        issue: Issue details including title, body, repository info

    Events emitted:
        - FLOW_STARTED: At flow start
        - CREW_FINISHED: After each crew (plan, implement)
        - STORY_COMPLETED: After each story implementation
        - FLOW_FINISHED: After final verification
    """
    import uuid
    from project_manager.config import settings as project_settings

    flow = SpecifyFlow()
    flow_identifier = f"{issue.repository.owner}/{issue.repository.repository}/{issue.id}"
    flow_id = uuid.uuid5(uuid.NAMESPACE_DNS, flow_identifier)
    inputs = dict(
        id=str(issue.flow_id),
        flow_id=flow_id,
        issue_id=issue.id,
        task=f"{issue.title}\n\n{issue.body}",
        path=f"{project_settings.DATA_PATH}/{issue.repository.owner}/{issue.repository.repository}",
        branch=f"{issue.id}-{sanitize_branch_name(issue.title)}",
        memory_prefix=f"{issue.repository.owner}/{issue.repository.repository}",
        repo_owner=issue.repository.owner,
        repo_name=issue.repository.repository,
        issue_author=issue.repository.owner,  # TODO: Get actual author from issue
        issue_title=issue.title,
        stage=SpecifyStage.STARTING,
        conversation_history=[{"role": "user", "content": issue.body, "source": "issue_body"}],
        project_config=issue.project_config.model_dump() if issue.project_config else {},
    )
    flow.kickoff(inputs=inputs)
