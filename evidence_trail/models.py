"""The public action and observation contract."""

from typing import Literal

from openenv.core.env_server.types import Action, Observation
from pydantic import Field


class TrailAction(Action):
    op: Literal["list", "read", "submit"] = Field(
        description="List files, read one file, or submit the final answer."
    )
    path: str = Field(default="", description="Filename for a read action.")
    entity: str = Field(default="", description="Entity ID with the largest verified increase.")
    delta: int = Field(default=0, description="Verified actual minus plan, as an integer.")
    evidence: list[str] = Field(
        default_factory=list,
        description="Record IDs supporting the submitted plan and final actual.",
    )


class TrailObservation(Observation):
    task: str = Field(default="", description="Investigation task ID.")
    message: str = Field(default="", description="Instruction or action result.")
    files: list[str] = Field(default_factory=list, description="Available filenames.")
    content: str = Field(default="", description="Content returned by a read action.")
    steps_left: int = Field(default=0, description="Actions remaining in the episode.")

