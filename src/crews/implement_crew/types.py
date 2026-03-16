from pydantic import BaseModel, Field


class ImplementOutput(BaseModel):
    """Output from implementation phase."""

    status: str = Field(default="done", description="Status")
    changes: str = Field(description="What was implemented")
    tests: str = Field(description="Tests that were written")

    title: str = Field(description="Commit Message title including conventional commit prefix")
    message: str = Field(description="The body of commit message")
    footer: str = Field(description="Commit message footer")
