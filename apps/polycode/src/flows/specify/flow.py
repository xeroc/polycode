"""Specify flow for pair-programming-style specification refinement."""

import logging

from crewai.flow.flow import router, listen, start
from crewai.flow.persistence import persist

from crews.conversation_crew import ConversationCrew, SpecOutput
from crews.plan_crew.plan_crew import PlanCrew
from crews.plan_crew.types import PlanOutput
from flows.base import FlowIssueManagement, KickoffIssue
from gitcore.operations import sanitize_branch_name
from modules.hooks import FlowEvent
from persistence.postgres import persistence

from .types import SpecifyFlowState, SpecifyStage

logger = logging.getLogger(__name__)

COMPLETION_KEYWORDS = {"lgtm", "lfg", "looks good", "looks good to me", "ship it", "ready"}


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
    def generate_response(self, state: SpecifyFlowState) -> SpecifyFlowState:
        """Generate initial clarifying questions from issue."""
        logger.info(f"❓ Generating initial questions for issue #{state.issue_id}")

        comments = self._fetch_comments(state)

        if not comments:
            logger.info("📭 No comments, returning")
            state.stage = SpecifyStage.WAITING
            return state

        # Add comments to history
        for comment in comments:
            state.conversation_history.append(
                {"body": comment["body"], "id": comment["id"], "author": comment["login"]}
            )
            state.last_processed_comment_id = comment["id"]

        # Check for completion keywords
        if comment and self._contains_completion_keyword(comment["body"]):  # pyright:ignore (last comment)
            logger.info(f"✅ Completion keyword detected: {comment['body']}")
            state.completion_keyword = comment["body"].strip()
            logger.info(f"🏁 Completing specify flow for issue #{state.issue_id}")
            state.specification_complete = True
            state.stage = SpecifyStage.COMPLETED
            self._emit(FlowEvent.ADD_LABEL, ["polycode:implement"])
            return state

        # Generate follow-up with ConversationCrew
        state.stage = SpecifyStage.PROCESSING

        result = (
            ConversationCrew()
            .crew()
            .kickoff(
                inputs=dict(
                    repo=self.state.repo,
                    branch=self.state.branch,
                    agents_md=self._root_agents_md,
                    file_in_repos=self.git_operations.list_tree(),
                    conversation_history=state.conversation_history,
                )
            )
        )

        # Post comment to issue
        comment_body: SpecOutput = result.pydantic  # pyright:ignore

        state.conversation_history.append({"role": "assistant", "content": comment_body, "source": "flow"})
        state.stage = SpecifyStage.WAITING

        return state

    @router(generate_response)
    def have_questions(self):
        if self.state.question:
            return "post_question"
        else:
            return "build_plan"

    @listen("post_question")
    def post_question(self):
        if not self.state.question:
            return
        logger.info(f"📝 Posting comment to #{self.state.issue_id}: {self.state.question[:100]}...")

        self._emit(FlowEvent.COMMENT, self.state.question)
        logger.info("💬 Posted initial questions, waiting for response")

    @listen("build_plan")
    def build_plan(self):
        result = (
            PlanCrew()
            .crew(agents_md_map=self._agents_md_map)
            .kickoff(
                inputs=dict(
                    task=self.state.task[:120],
                    repo=self.state.repo,
                    branch=self.state.branch,
                    agents_md=self._root_agents_md,
                    file_in_repos=self.git_operations.list_tree(),
                )
            )
        )

        output: PlanOutput = result.pydantic  # type: ignore
        self.state.stories = output.stories
        self.state.build_cmd = output.build_cmd
        self.state.test_cmd = output.test_cmd

        logger.info(f"🔖 Planned {len(output.stories)} stories")
        for current_story in output.stories:
            logger.info(f"  |- 🔖 {current_story.description}")

        self._emit(FlowEvent.STORIES_PLANNED)

    # Helper methods
    def _contains_completion_keyword(self, text: str) -> bool:
        """Check if text contains a completion keyword."""
        text_lower = text.lower().strip()
        return any(kw in text_lower for kw in COMPLETION_KEYWORDS)

    def _fetch_comments(self, state: SpecifyFlowState) -> list[dict]:
        """Fetch new comments from issue author."""
        # TODO: Implement with GitHubProjectManager
        # Filter by: author == state.issue_author
        # Filter by: id > state.last_processed_comment_id
        return []


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
