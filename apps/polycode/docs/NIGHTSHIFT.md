# 🌙 Night Shift Integration Plan

> Extracting the best patterns from Jamon Holmgren's "Night Shift" agentic workflow
> into Polycode's review crew and error handling.

---

## Source

**The "Night Shift" Agentic Workflow** by Jamon Holmgren (March 14, 2026)

Key ideas:

- Human time is expensive, agent time is cheap
- Day shift: humans write specs, organize thinking
- Night shift: agents execute autonomously with multi-perspective review
- 6 specialized review personas each "own" docs and suggest improvements
- Postmortem-first: when agent fails, fix docs/workflow FIRST, then fix code
- Continuous improvement loop: every failure makes the system better

---

## What Polycode Has That Night Shift Doesn't

| Feature                | Polycode     | Night Shift |
| ---------------------- | ------------ | ----------- |
| Self-hosted            | ✅           | ❌          |
| GitHub-native          | ✅           | ❌          |
| Policy Engine          | ✅ (Phase 1) | ❌          |
| Semantic Merge (Weave) | ✅           | ❌          |
| Resume/Cancel Flows    | ✅           | ❌          |
| Git Notes Integration  | ✅           | ❌          |
| Retro Agent            | ✅ (Phase 3) | ❌          |
| Hook System            | ✅           | ❌          |
| Celery task retry      | ✅           | ❌          |

---

## What Night Shift Has That We're Integrating

### 1. Multi-Persona Review Crew

6 specialized reviewers + 1 manager agent with delegation.

### 2. Postmortem-First Failure Handling

`DocImprovementsAgent` triggered on flow errors. Fix docs, not just code.

---

## Implementation Plan

### Phase 1: Enhanced Review Crew

#### 1.1 Update `types.py`

Add `ReviewerFeedback` and enhance `ReviewOutput`:

```python
class ReviewerFeedback(BaseModel):
    """Feedback from individual reviewer persona."""
    reviewer_name: str
    reviewer_role: str
    decision: Literal["approved", "changes_requested", "blocked"]
    feedback: list[str] = []
    doc_improvements: list[str] = []

class ReviewOutput(BaseModel):
    """Aggregated multi-persona review output."""
    overall_decision: Literal["approved", "changes_requested", "blocked"]
    status: str
    reviewer_feedback: list[ReviewerFeedback]
    required_changes: list[str] = []
    doc_improvements: list[str] = []
```

#### 1.2 Agent Hierarchy

```
review_manager (allow_delegation=True)
    ├── design_reviewer (allow_delegation=False)
    ├── architect_reviewer (allow_delegation=False)
    ├── domain_expert_reviewer (allow_delegation=False)
    ├── code_expert_reviewer (allow_delegation=False)
    ├── performance_expert_reviewer (allow_delegation=False)
    └── human_advocate_reviewer (allow_delegation=False)
```

Manager uses CrewAI `Process.hierarchical` to delegate to specialists.

#### 1.3 Reviewer Personas & Doc Ownership

| Persona            | Doc Owned                    | Focus                                       |
| ------------------ | ---------------------------- | ------------------------------------------- |
| Designer           | `design_guidelines.md`       | UX/UI, accessibility, visual consistency    |
| Architect          | `architecture_principles.md` | Structural soundness, scalability, patterns |
| Domain Expert      | `domain_knowledge.md`        | Business logic, edge cases, domain rules    |
| Code Expert        | `code_standards.md`          | Code quality, style, test coverage          |
| Performance Expert | `performance_guidelines.md`  | Bottlenecks, resource usage, efficiency     |
| Human Advocate     | `ux_requirements.md`         | Maintainability, onboarding, clarity        |

Each reviewer suggests improvements to their owned doc when they spot gaps.

#### 1.4 Config Files

**`config/agents.yaml`** — 7 agents (1 manager + 6 specialists)

**`config/tasks.yaml`** — 1 manager coordination task + 6 specialist review tasks

Manager task delegates to all 6 specialists, collects feedback, produces
unified `ReviewOutput`.

#### 1.5 Crew Process

```python
Crew(
    agents=self.agents,
    tasks=self.tasks,
    process=Process.hierarchical,
    manager_llm=GLMJSONLLM(),
)
```

---

### Phase 2: Postmortem-First Failure Handling

#### 2.1 DocImprovementsAgent

Standalone agent (not part of a crew) that analyzes failures and suggests
doc improvements. Lives in the ReviewCrew module as a utility method.

```python
# In review_crew.py
from crewai import Agent

class ReviewCrew(PolycodeCrewMixin):
    ...

    def apply_doc_improvements(
        self,
        error_context: str,
        flow_id: str,
        label: str,
    ) -> list[str]:
        """Analyze failure and suggest doc/workflow improvements.

        Night Shift pattern: when agent fails, fix docs/workflow FIRST,
        then fix code. This agent analyzes the failure context and returns
        structured suggestions for doc improvements.

        Args:
            error_context: The error message and surrounding context
            flow_id: ID of the failed flow
            label: Flow label (e.g., "ralph")

        Returns:
            List of suggested doc improvements
        """
        agent = Agent(
            role="Documentation Improvement Analyst",
            goal="Analyze failures and identify documentation or workflow gaps that led to the failure",
            backstory=(
                "You're a postmortem specialist. When an AI agent fails, you don't "
                "just look at the code — you look at what docs, skills, or workflow "
                "instructions could have prevented the failure. You suggest concrete "
                "improvements to documentation that will prevent similar failures."
            ),
            llm=GLMJSONLLM(),
            verbose=False,
        )
        result = agent.kickoff(
            f"Analyze this failure and suggest doc improvements:\n\n"
            f"Flow: {label}\nFlow ID: {flow_id}\n\n"
            f"Error context:\n{error_context}\n\n"
            f"Return a list of specific, actionable doc improvements that would "
            f"prevent this failure in the future."
        )
        return result.raw.split("\n")
```

#### 2.2 Hook Integration

Add `on_flow_error` hook in the hooks module that triggers the
DocImprovementsAgent:

```python
# In modules/hooks/
@hookimpl
def on_flow_error(event, flow_id, state, result, label):
    """Postmortem-first: analyze failure, suggest doc improvements.

    Night Shift pattern: don't just fix code — fix the docs/workflow
    that led to the wrong decision.
    """
    from crews.review_crew.review_crew import ReviewCrew

    crew = ReviewCrew()
    improvements = crew.apply_doc_improvements(
        error_context=str(result),
        flow_id=flow_id,
        label=label,
    )

    # Store improvements for human review
    # (could write to file, post as issue comment, etc.)
    logger.warning(f"📋 Doc improvements suggested: {improvements}")
```

#### 2.3 Retry via Celery

No custom retry logic needed. Flows already run as Celery tasks with
auto-retry on failure. After doc improvements are applied, the next
Celery retry will use updated context.

```
Flow fails → on_flow_error hook fires → DocImprovementsAgent analyzes
→ improvements stored → Celery auto-retries → next run benefits from improvements
```

---

## Files to Modify

| File                                                     | Change                                         |
| -------------------------------------------------------- | ---------------------------------------------- |
| `apps/polycode/src/crews/review_crew/types.py`           | Add `ReviewerFeedback`, enhance `ReviewOutput` |
| `apps/polycode/src/crews/review_crew/config/agents.yaml` | 7 agents                                       |
| `apps/polycode/src/crews/review_crew/config/tasks.yaml`  | 7 tasks                                        |
| `apps/polycode/src/crews/review_crew/review_crew.py`     | Hierarchical crew + `apply_doc_improvements`   |
| `apps/polycode/src/modules/hooks/`                       | Add `on_flow_error` hookimpl                   |

---

## Success Criteria

- [ ] Manager agent delegates to all 6 specialists via CrewAI delegation
- [ ] Each specialist provides role-specific feedback
- [ ] Manager aggregates feedback into unified decision
- [ ] Doc improvement suggestions captured in ReviewOutput
- [ ] `apply_doc_improvements()` runs DocImprovementsAgent on failure
- [ ] `on_flow_error` hook triggers postmortem analysis
- [ ] Celery auto-retry benefits from improved docs
- [ ] Type-safe with `output_pydantic=ReviewOutput`
- [ ] Tests pass for all new functionality

---

## Not In Scope

- ❌ Agent-watching-agent coordination (explicitly rejected)
- ❌ Spec-driven workflow (future consideration)
- ❌ New flow module (using existing review_crew)

---

_"Build something engineers trust — not something that demos well."_
