#!/usr/bin/env python
from typing import Any, Dict

from crewai.flow.flow import Flow, listen, start

from .types import FeatureDevState
from .crews.feature_dev_crew import FeatureDevCrew


class FeatureDevFlow(Flow[FeatureDevState]):
    """
    Feature development workflow with state persistence and conditional routing.
    """

    # model = "gpt-4o-mini"

    @start()
    def startup(self) -> Dict[str, Any]:
        inputs  = dict(repo="https://github.com/xeroc/xeroc",
                       task="add a new profile item that i do ai agents now",
                    branch="main",
                    # severity = "medium",
                    # affected_area = "unknown",
                    # reproduction = "N/A",
                    # problem_statement = "bug",
                    #    task="fix bug",
                    build_cmd="exit 0;",
                    test_cmd="exit 0;",
                    current_story="story",
                    completed_stories="old story",
                    current_story_title="title",
                    current_story_id=1,
                    results="",
                    pr="",
                    changes="",
                    #    regression_test="",
                    #    verified=True,
                      )

        result = (
            FeatureDevCrew()
            .crew()
            .kickoff(inputs=inputs)
        )

        return {"result": result}

    @listen(startup)
    def create_pr(self, test_result: Dict[str, Any]) -> Dict[str, Any]:
        """Step 7: Create pull request."""
        return {"pr_url": None}


def kickoff():
    """
    Run the flow.
    """
    feature_dev_flow = FeatureDevFlow()
    feature_dev_flow.kickoff()


def plot():
    """
    Plot the flow.
    """
    feature_dev_flow = FeatureDevFlow()
    feature_dev_flow.plot()


if __name__ == "__main__":
    kickoff()
