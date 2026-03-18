import fnmatch
import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from github_app.models import LabelFlowMapping

logger = logging.getLogger(__name__)


class LabelFlowMapper:
    def __init__(self, db_session: Session):
        self.db_session = db_session

    def get_flow_for_label(
        self, installation_id: int, label_name: str, repo_slug: str
    ) -> Optional[LabelFlowMapping]:
        mappings = (
            self.db_session.query(LabelFlowMapping)
            .filter(
                LabelFlowMapping.installation_id == installation_id,
                LabelFlowMapping.label_name == label_name,
                LabelFlowMapping.is_active.is_(True),
            )
            .order_by(LabelFlowMapping.priority.desc())
            .all()
        )

        for mapping in mappings:
            pattern: Optional[str] = mapping.repo_pattern  # type: ignore
            if self._matches_repo_pattern(pattern, repo_slug):
                logger.info(
                    f"Matched label '{label_name}' to flow '{mapping.flow_name}' "
                    f"for repo '{repo_slug}' (installation: {installation_id})"
                )
                return mapping

        logger.debug(
            f"No flow mapping found for label '{label_name}' in repo '{repo_slug}' "
            f"(installation: {installation_id})"
        )
        return None

    def _matches_repo_pattern(
        self, pattern: Optional[str], repo_slug: str
    ) -> bool:
        if not pattern:
            return True

        return fnmatch.fnmatch(repo_slug, pattern)

    def create_mapping(
        self,
        installation_id: int,
        label_name: str,
        flow_name: str,
        repo_pattern: Optional[str] = None,
        priority: int = 0,
        config: Optional[Dict[str, Any]] = None,
    ) -> LabelFlowMapping:
        """Create a new label-to-flow mapping."""
        mapping = LabelFlowMapping(
            installation_id=installation_id,
            label_name=label_name,
            flow_name=flow_name,
            repo_pattern=repo_pattern,
            priority=priority,
            config=config or {},
        )

        self.db_session.add(mapping)
        self.db_session.commit()

        logger.info(
            f"Created label-flow mapping: '{label_name}' -> '{flow_name}' "
            f"(installation: {installation_id}, pattern: {repo_pattern})"
        )

        return mapping

    def update_mapping(
        self, mapping_id: int, **kwargs
    ) -> Optional[LabelFlowMapping]:
        """Update an existing mapping."""
        mapping = (
            self.db_session.query(LabelFlowMapping)
            .filter(LabelFlowMapping.id == mapping_id)
            .first()
        )

        if not mapping:
            return None

        for key, value in kwargs.items():
            if hasattr(mapping, key):
                setattr(mapping, key, value)

        self.db_session.commit()
        logger.info(f"Updated label-flow mapping {mapping_id}")
        return mapping

    def delete_mapping(self, mapping_id: int) -> bool:
        """Delete a label-to-flow mapping."""
        mapping = (
            self.db_session.query(LabelFlowMapping)
            .filter(LabelFlowMapping.id == mapping_id)
            .first()
        )

        if not mapping:
            return False

        self.db_session.delete(mapping)
        self.db_session.commit()

        logger.info(f"Deleted label-flow mapping {mapping_id}")
        return True

    def list_mappings(
        self, installation_id: Optional[int] = None
    ) -> list[LabelFlowMapping]:
        """List all label-to-flow mappings, optionally filtered by installation."""
        query = self.db_session.query(LabelFlowMapping).filter(
            LabelFlowMapping.is_active.is_(True)
        )

        if installation_id:
            query = query.filter(
                LabelFlowMapping.installation_id == installation_id
            )

        return query.order_by(LabelFlowMapping.priority.desc()).all()
