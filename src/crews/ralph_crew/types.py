from pydantic import BaseModel, Field


class RalphOutput(BaseModel):
    changes: str = Field(description="What was implemented")
    title: str = Field(description="Commit title with conventional prefix")
    message: str = Field(description="Commit message body")
    footer: str = Field(default="", description="Commit footer")
