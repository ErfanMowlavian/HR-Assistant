"""Pydantic v2 request/response schemas for the HTTP API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class JobDescriptionCreate(BaseModel):
    """Payload HR sends to create a JD."""

    title: str = Field(min_length=1, max_length=255)
    text: str = Field(min_length=1, description="The full Persian JD text.")


class JobDescriptionRead(BaseModel):
    """A JD as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    text: str
    created_at: datetime
