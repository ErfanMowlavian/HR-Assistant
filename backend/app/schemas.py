"""Pydantic v2 request/response schemas for the HTTP API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.llm.types import JDRequirements


class JobDescriptionCreate(BaseModel):
    """Payload HR sends to create a JD."""

    title: str = Field(min_length=1, max_length=255)
    text: str = Field(min_length=1, description="The full Persian JD text.")


class JobDescriptionRead(BaseModel):
    """A JD as returned by the API.

    `requirements` is the structured extraction (null if extraction has not
    succeeded yet); `extraction_ok` lets the UI flag a failed extraction so HR
    can re-run or fill the requirements in by hand.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    text: str
    created_at: datetime
    requirements: JDRequirements | None = None

    @computed_field
    @property
    def extraction_ok(self) -> bool:
        return self.requirements is not None


# HR's review/correction of the extracted requirements is just a new
# JDRequirements payload, validated by the same schema.
RequirementsUpdate = JDRequirements
