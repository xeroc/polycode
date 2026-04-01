"""Specify flow for pair-programming-style specification refinement."""

import logging

from crewai.flow.flow import listen, router, start

from crews.conversation_crew import ConversationCrew, SpecOutput
from crews.plan_crew.plan_crew import PlanCrew
from crews.plan_crew.types import PlanOutput
from flows.base import FlowIssueManagement, KickoffIssue
from gitcore.operations import sanitize_branch_name
from modules.hooks import FlowEvent

from .types import SpecifyFlowState, SpecifyStage

logger = logging.getLogger(__name__)

COMPLETION_KEYWORDS = {"lgtm", "lfg", "looks good", "looks good to me", "ship it", "ready"}


# @persist(persistence=persistence, verbose=False)
class SpecifyFlow(FlowIssueManagement[SpecifyFlowState]):
    """Flow for refining specifications via GitHub issue comments."""

    @start()
    def setup(self):
        """Initialize flow and emit FLOW_STARTED event."""
        logger.info("🚀 Specify Loop starting...")
        self._emit(FlowEvent.FLOW_STARTED, label="specify")
        self._setup()

    @listen(setup)
    def generate_response(self):
        if self.state.questions or self.state.specifications:
            logger.info("Already have questions or specs, proceeding to planning")
            return
        """Generate initial clarifying questions from issue."""
        logger.info(f"❓ Generating questions/specs for issue #{self.state.issue_id}")

        if not self.state.conversation_history:
            logger.info("📭 No comments, returning")
            self.state.stage = SpecifyStage.WAITING
            return

        # Check for completion keywords
        last_comment = self.state.conversation_history[-1]
        if last_comment and self._contains_completion_keyword(last_comment.body):  # pyright:ignore (last last_comment)
            logger.info(f"✅ Completion keyword detected: {last_comment.body}")
            self.state.completion_keyword = last_comment.body.strip()
            logger.info(f"🏁 Completing specify flow for issue #{self.state.issue_id}")
            self.state.specification_complete = True
            self.state.stage = SpecifyStage.COMPLETED
            self._emit(FlowEvent.ADD_LABEL, ["polycode:implement"])
            return

        # Generate follow-up with ConversationCrew
        self.state.stage = SpecifyStage.PROCESSING

        result = (
            ConversationCrew()
            .crew()
            .kickoff(
                inputs=dict(
                    repo=self.state.repo,
                    branch=self.state.branch,
                    agents_md=self._root_agents_md,
                    file_in_repos=self.git_operations.list_tree(),
                    issue_id=self.state.issue_id,
                    task=self.state.task,
                    conversation_history=[x.model_dump() for x in self.state.conversation_history],
                )
            )
        )

        # Post comment to issue
        comment_body: SpecOutput = result.pydantic  # type: ignore
        if comment_body.questions:
            self.state.questions = comment_body.questions
            self.state.stage = SpecifyStage.WAITING
        elif comment_body.specifications:
            self.state.specifications = comment_body.specifications
            self.state.assumptions = comment_body.assumptions
            self.state.requirements = comment_body.requirements
            self.state.stage = SpecifyStage.PROCESSING

        return

    @router(generate_response)
    def have_questions(self):
        if self.state.questions:
            return "post_question"
        else:
            return "build_plan"

    @listen("post_question")
    def post_questions(self):
        if not self.state.questions:
            return
        logger.info(f"📝 Posting comment to #{self.state.issue_id}: {len(self.state.questions)} questions")
        comment = """## Questions\n\n"""
        for index, question in enumerate(self.state.questions):
            comment += f"{index}. {question}\n"

        self._emit(FlowEvent.COMMENT, result=comment)
        logger.info("💬 Posted comment, waiting for response")

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
        project_config=issue.project_config.model_dump() if issue.project_config else {},
        conversation_history=issue.comments,
        flow_name="specify",
    )
    flow.kickoff(inputs=inputs)
