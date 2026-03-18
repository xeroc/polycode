---
name: implement_task
agent: developer
output_pydantic: ImplementOutput
---

# Description

You are implementing a user story with a specialized approach.

TASK (overall):
{task}

REPO: {repo}
BRANCH: {branch}
BUILD_CMD: {build_cmd}
TEST_CMD: {test_cmd}

CREWAI REFERENCE GUIDE (AGENTS.md):
{agents_md}

CURRENT STORY:
{current_story}

TECH STACK:
{tech_stack}

ARCHITECTURE:
{architecture}

CONFIGURATION:
{configuration}

TOOLS:

- FileReadTool
- FileWriterTool
- DirectoryReadTool
- ExecTool
- AgentsMDLoaderTool: Load AGENTS.md files from subdirectories

CUSTOM INSTRUCTIONS:

- This is a custom task template for specialized implementations
- Follow domain-specific patterns when applicable
- Be extra careful with error handling

INSTRUCTIONS:

1. Read progress log to understand codebase patterns
2. Implement this story only
3. Write comprehensive tests
4. Run typecheck / build
5. Run tests to confirm they pass
6. Update progress log with codebase patterns found

# Expected Output

Implemented story with details on changes and tests added. Include:

- What files were modified
- What tests were added
- Any notes about the implementation approach
