#!/usr/bin/env python
from typing import Any, Dict

from crewai.flow.flow import Flow, listen, start
from .crews.bug_fix_crew import (
    BugFixCrew,
)
from .types import BugFixState


class BugFixFlow(Flow[BugFixState]):
    """
    Bug fix workflow with state persistence and conditional routing.

    This Flow implements antfarm bug-fix workflow using CrewAI's Flow system:
    - State persistence to SQLite (@persist)
    - Conditional routing for retry logic
    - Human feedback for critical decisions
    - Agent-based task execution
    """

    # model = "gpt-4o-mini"

    @start()
    def triage(self) -> Dict[str, Any]:
        """
        Step 1: Analyze bug report, reproduce issue, classify severity.
        """
        print("🔍 Step 1/6: Triage - Analyzing bug report...")

        inputs  = dict(repo="xeroc/xeroc",
                      branch="main",
                    severity = "medium",
                    affected_area = "unknown",
                    reproduction = "N/A",
                    problem_statement = "bug",
                       task="fix bug",
                       build_cmd="exit 0;",
                       test_cmd="exit 0;",
                       root_cause="",
                      )

        print(f"✅ Triage complete: {inputs.get("severity")} severity")
        print(f"   Repository: {inputs.get("repo")}")
        print(f"   Branch: {inputs.get("branch")}")

        return self.state

    @listen(triage)
    def fix_bug(self, triage_result: Dict[str, Any]) -> Dict[str, Any]:
        print("🔬 Step 2/2: Let the crew work...")
        print(triage_result)

        inputs  = dict(repo="xeroc/xeroc",
                      branch="main",
                    severity = "medium",
                    affected_area = "unknown",
                    reproduction = "N/A",
                    problem_statement = "bug",
                       task="fix bug",
                       build_cmd="exit 0;",
                       test_cmd="exit 0;",
                       root_cause="",
                       fix_approach="",
                       changes="",
                       regression_test="",
                       verified=True,
                      )

        output = (
            BugFixCrew()
            .crew()
            .kickoff(inputs=inputs)
        )
        print(output)

        print(f"✅ bug fixed: {self.inputs}")

        return { }


def kickoff():
    """
    Run the flow.
    """
    bug_fix_flow = BugFixFlow()
    bug_fix_flow.kickoff()


def plot():
    """
    Plot the flow.
    """
    bug_fix_flow = BugFixFlow()
    bug_fix_flow.plot()


if __name__ == "__main__":
    kickoff()
