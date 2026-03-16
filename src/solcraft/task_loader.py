import logging
import re
from pathlib import Path
from typing import Any

import yaml

from .types import TaskTemplate

logger = logging.getLogger(__name__)


def parse_task_template_from_markdown(content: str) -> TaskTemplate | None:
    """Parse a markdown file with YAML frontmatter into a TaskTemplate.

    Expected format:
    ---
    name: implement_task
    agent: developer
    context:
      - setup_task
    output_pydantic: ImplementOutput
    ---
    # Description
    Your task description here with {variables}

    # Expected Output
    What the output should look like
    """
    frontmatter_pattern = re.compile(
        r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL
    )
    match = frontmatter_pattern.match(content.strip())

    if not match:
        logger.warning("No YAML frontmatter found in template")
        return None

    try:
        frontmatter = yaml.safe_load(match.group(1))
        body = match.group(2).strip()

        sections = _parse_body_sections(body)

        return TaskTemplate(
            name=frontmatter.get("name", "unnamed_task"),
            description=sections.get("description", ""),
            expected_output=sections.get("expected_output", ""),
            agent=frontmatter.get("agent", "developer"),
            context=frontmatter.get("context"),
            output_pydantic=frontmatter.get("output_pydantic"),
        )
    except yaml.YAMLError as e:
        logger.error(f"Failed to parse frontmatter: {e}")
        return None


def _parse_body_sections(body: str) -> dict[str, str]:
    """Parse markdown body into sections based on headers."""
    sections: dict[str, str] = {}
    current_section = "description"
    current_content: list[str] = []

    for line in body.split("\n"):
        header_match = re.match(r"^#\s+(.+)$", line)
        if header_match:
            if current_content:
                sections[current_section] = "\n".join(current_content).strip()
            current_section = header_match.group(1).lower().replace(" ", "_")
            current_content = []
        else:
            current_content.append(line)

    if current_content:
        sections[current_section] = "\n".join(current_content).strip()

    return sections


def load_task_template(path: str | Path) -> TaskTemplate | None:
    """Load a task template from a markdown file."""
    path = Path(path)
    if not path.exists():
        logger.error(f"Task template not found: {path}")
        return None

    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    return parse_task_template_from_markdown(content)


def load_task_templates(paths: list[str]) -> dict[str, TaskTemplate]:
    """Load multiple task templates from markdown files."""
    templates: dict[str, TaskTemplate] = {}

    for path in paths:
        template = load_task_template(path)
        if template:
            templates[template.name] = template
            logger.info(
                f"📄 Loaded task template: {template.name} from {path}"
            )

    return templates


def task_template_to_crewai_config(template: TaskTemplate) -> dict[str, Any]:
    """Convert a TaskTemplate to CrewAI task config format."""
    config: dict[str, Any] = {
        "description": template.description,
        "expected_output": template.expected_output,
        "agent": template.agent,
    }

    if template.context:
        config["context"] = template.context

    return config


def merge_task_configs(
    base_configs: dict[str, Any],
    templates: dict[str, TaskTemplate],
) -> dict[str, Any]:
    """Merge task templates with base configs, templates take precedence."""
    merged = dict(base_configs)

    for name, template in templates.items():
        merged[name] = task_template_to_crewai_config(template)

    return merged
