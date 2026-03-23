"""Conversation-driven specification flow."""

import logging
from typing import List

from crewai.flow.flow import listen, start

from crews.conversation_crew import ConversationCrew
from crews.plan_crew.types import Story
from flows.base import FlowIssueManagement
from project_manager.github_conversation import GitHubConversationManager

from .types import (
    ConversationFlowState,
    ConversationMessage,
    ConversationStage,
    NewCommentInput,
    ReactionInput,
)

logger = logging.getLogger(__name__)


class ConversationFlow(FlowIssueManagement[ConversationFlowState]):
    """Flow for conversation-driven specification via GitHub comments."""

    conversation_crew: ConversationCrew | None = None

    @property
    def _github_manager(self) -> GitHubConversationManager:
        if not self.state.project_config:
            raise ValueError("project_config not specified!")
        return GitHubConversationManager(self.state.project_config)

    @start()
    def initialize_conversation(self):
        """Initialize conversation from issue opening."""
        logger.info(f"🗣️ Starting conversation for issue #{self.state.issue_id}")

        self.conversation_crew = ConversationCrew()

        initial_message = (
            "## 🤖 Specification Bot Activated\n\n"
            "I'll help you refine this feature into a clear specification. "
            "I'll ask questions to clarify requirements, then propose a specification for your approval.\n\n"
            "**To approve a specification or story plan, add a 👍 reaction to my comment.**\n\n"
            "Let's start!"
        )
        self._github_manager.add_comment(self.state.issue_id, initial_message)
        self._ask_specification_question()

    def _ask_specification_question(self):
        """Generate and post a specification question."""
        crew = self.conversation_crew
        if not crew:
            return

        history = "\n\n".join(f"**{msg.author}**: {msg.content}" for msg in self.state.messages)

        crew_instance = crew.crew()
        result = crew_instance.kickoff(
            inputs={
                "title": self.state.task,
                "body": self.state.commit_message or "",
                "conversation_history": history or "No conversation yet",
            }
        )

        response_text = str(result) if result else "No response"
        self._github_manager.add_comment(self.state.issue_id, response_text)

        self.state.messages.append(
            ConversationMessage(
                author="llm",
                content=response_text,
            )
        )
        self.state.stage = ConversationStage.SPEC_ELCITATION

    @listen(initialize_conversation)
    def handle_new_comment(self, input_data: NewCommentInput):
        """Handle new comment from user."""
        logger.info(f"💬 New comment from {input_data.author}")

        self.state.messages.append(
            ConversationMessage(
                author=input_data.author,
                content=input_data.content,
            )
        )

        if input_data.thumbs_up:
            logger.info("👍 Thumbs up detected, moving to next stage")
            self._handle_approval()
        else:
            self._ask_specification_question()

    @listen(handle_new_comment)
    def handle_reaction(self, input_data: ReactionInput):
        """Handle thumbs up reaction."""
        if input_data.reaction == "+1":
            logger.info("👍 Thumbs up reaction detected")
            self.state.thumbs_up_given = True
            self._handle_approval()

    def _handle_approval(self):
        """Handle specification approval and move to story planning."""
        if self.state.stage == ConversationStage.SPEC_ELCITATION:
            logger.info("✅ Specification approved, moving to story breakdown")
            self.state.stage = ConversationStage.SPEC_APPROVAL
            self._break_down_stories()
        elif self.state.stage == ConversationStage.STORY_BREAKDOWN:
            logger.info("✅ Stories approved, initializing Ralph loop")
            self.state.stage = ConversationStage.STORY_APPROVAL
            self._init_ralph_loop()

    def _break_down_stories(self):
        """Break down approved specification into stories."""
        if not self.conversation_crew:
            return

        crew = self.conversation_crew
        spec = self.state.specification or self.state.messages[-1].content

        crew_instance = crew.crew()
        result = crew_instance.kickoff(
            inputs={
                "specification": spec,
            }
        )

        crew_output = result
        if hasattr(result, "result"):
            crew_output = result.result  # pyright: ignore

        stories_text = "## 📋 Proposed Stories\n\n"

        stories: List[Story] = crew_output.pydantic  # type: ignore[assignment]

        for story in stories:
            self.state.stories.append(story)
            stories_text += f" - [{' ' if story.completed else 'x'}] {story.description}\n\n---\n\n"

        stories_text += "\nPlease review these stories. **Add 👍 to this comment when you approve the plan.**"

        self._github_manager.add_comment(self.state.issue_id, stories_text)
        self.state.specification = spec
        self.state.stage = ConversationStage.STORY_BREAKDOWN

    def _init_ralph_loop(self):
        """Initialize Ralph loop with approved stories."""
        if not self.state.stories:
            logger.warning("No stories to execute")
            return

        next_story = None
        for story in self.state.stories:
            if not story.completed:
                next_story = story
                self.state.approved_story_id = story.id
                break

        if not next_story:
            logger.info("All stories completed!")
            self.state.stage = ConversationStage.COMPLETED
            return

        logger.info(f"🚀 Initializing Ralph for story: {next_story.title}")

        conversation_summary = "\n".join(f"- {msg.author}: {msg.content}" for msg in self.state.messages[-5:])

        if self.conversation_crew:
            crew_instance = self.conversation_crew.crew()
            result = crew_instance.kickoff(
                inputs={
                    "specification": self.state.specification,
                    "story": next_story.model_dump(),
                    "conversation_summary": conversation_summary,
                }
            )

            response_text = str(result) if result else "No response"
            brief = (
                f"## 🚀 Starting Development\n\n"
                f"**Story:** {next_story.title}\n\n"
                f"---\n\n"
                f"{response_text}\n\n"
                f"Development in progress..."
            )
            self._github_manager.add_comment(self.state.issue_id, brief)

        logger.info("Transitioning to Ralph execution phase")
        self.state.stage = ConversationStage.RALPH_INIT

    def check_ralph_completion(self):
        """Check if Ralph loop completed the current story."""
        if self.state.build_success and self.state.test_success:
            logger.info("✅ Story completed successfully")

            for story in self.state.stories:
                if story.id == self.state.approved_story_id:
                    story.completed = True
                    break

            self._github_manager.add_comment(
                self.state.issue_id,
                f"## ✅ Story Completed\n\n"
                f"Story {self.state.approved_story_id} completed successfully.\n\n"
                f"Review the changes and provide feedback.",
            )

            self._break_down_stories()
        elif self.state.stage == ConversationStage.RALPH_EXECUTION:
            logger.info("⏳ Ralph execution in progress")
            return "wait"
        else:
            logger.error("❌ Ralph execution failed")
            return "error"

    @listen("wait")
    def wait_for_completion(self):
        """Wait for Ralph to complete."""
        return "continue"

    @listen("error")
    def handle_ralph_error(self):
        """Handle Ralph execution errors."""
        logger.error("Ralph execution error, requesting feedback")
        self._github_manager.add_comment(
            self.state.issue_id,
            "## ❌ Error\n\nDevelopment encountered an error. Please review and provide guidance.",
        )
        self.state.stage = ConversationStage.INIT
