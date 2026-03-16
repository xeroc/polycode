"""Enhanced GitHub manager with reaction support."""

import logging
from typing import Optional

from .github import GitHubProjectManager

log = logging.getLogger(__name__)


class GitHubConversationManager(GitHubProjectManager):
    """GitHub manager with conversation and reaction support."""

    def get_comment_reactions(
        self, issue_number: int, comment_id: int
    ) -> list[dict]:
        """Get reactions on a specific comment.

        Args:
            issue_number: Issue number
            comment_id: Comment ID

        Returns:
            List of reactions with user and content
        """
        try:
            issue = self.repo.get_issue(issue_number)
            comment = issue.get_comment(comment_id)
            reactions = []

            for reaction in comment.get_reactions():
                reactions.append(
                    {
                        "user": reaction.user.login if reaction.user else None,
                        "content": reaction.content,
                        "created_at": (
                            reaction.created_at.isoformat()
                            if reaction.created_at
                            else None
                        ),
                    }
                )

            log.info(
                f"Found {len(reactions)} reactions on comment {comment_id}"
            )
            return reactions

        except Exception as e:
            log.error(f"Failed to get reactions on comment {comment_id}: {e}")
            return []

    def has_thumbs_up_reaction(
        self, issue_number: int, comment_id: int
    ) -> bool:
        """Check if a comment has a thumbs up reaction from the issue author.

        Args:
            issue_number: Issue number
            comment_id: Comment ID

        Returns:
            True if thumbs up from issue author exists
        """
        try:
            issue = self.repo.get_issue(issue_number)
            issue_author = issue.user.login

            reactions = self.get_comment_reactions(issue_number, comment_id)

            for reaction in reactions:
                if (
                    reaction["content"] == "+1"
                    and reaction["user"] == issue_author
                ):
                    log.info(f"Thumbs up from {issue_author} detected")
                    return True

            return False

        except Exception as e:
            log.error(
                f"Failed to check thumbs up on comment {comment_id}: {e}"
            )
            return False

    def get_latest_comments(
        self, issue_number: int, since_id: Optional[int] = None
    ) -> list[dict]:
        """Get latest comments on an issue.

        Args:
            issue_number: Issue number
            since_id: Only return comments after this ID

        Returns:
            List of comment dictionaries
        """
        try:
            issue = self.repo.get_issue(issue_number)
            comments = []

            for comment in issue.get_comments():
                if since_id and comment.id <= since_id:
                    continue

                # Check for thumbs up reaction
                has_thumbs_up = self.has_thumbs_up_reaction(
                    issue_number, comment.id
                )

                comments.append(
                    {
                        "id": comment.id,
                        "user": comment.user.login if comment.user else None,
                        "body": comment.body,
                        "created_at": (
                            comment.created_at.isoformat()
                            if comment.created_at
                            else None
                        ),
                        "thumbs_up": has_thumbs_up,
                    }
                )

            log.info(f"Retrieved {len(comments)} new comments")
            return comments

        except Exception as e:
            log.error(f"Failed to get comments for issue {issue_number}: {e}")
            return []

    def get_issue_with_reactions(self, issue_number: int) -> dict:
        """Get issue with reaction information.

        Args:
            issue_number: Issue number

        Returns:
            Dictionary with issue details and reaction info
        """
        try:
            issue = self.repo.get_issue(issue_number)

            # Get reactions on the issue itself
            reactions = []
            for reaction in issue.get_reactions():
                reactions.append(
                    {
                        "user": reaction.user.login if reaction.user else None,
                        "content": reaction.content,
                        "created_at": (
                            reaction.created_at.isoformat()
                            if reaction.created_at
                            else None
                        ),
                    }
                )

            return {
                "id": issue.number,
                "title": issue.title,
                "body": issue.body,
                "author": issue.user.login if issue.user else None,
                "state": issue.state,
                "reactions": reactions,
            }

        except Exception as e:
            log.error(f"Failed to get issue {issue_number}: {e}")
            return {}
