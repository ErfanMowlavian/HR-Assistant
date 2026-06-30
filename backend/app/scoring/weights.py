"""Scoring weights (ADR-0002). Defaults ship; HR can override per request.

The four criteria, in priority order: required-skill coverage (highest),
nice-to-have coverage, experience-years match, education/seniority match. The
scorer renormalizes over whichever criteria actually apply to a given JD, so the
absolute weights below need not sum to 1 — only their relative sizes matter.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ScoreWeights(BaseModel):
    """Relative importance of each scoring criterion."""

    required_skills: float = Field(default=0.50, ge=0)
    nice_to_have_skills: float = Field(default=0.15, ge=0)
    experience: float = Field(default=0.20, ge=0)
    education: float = Field(default=0.15, ge=0)


DEFAULT_WEIGHTS = ScoreWeights()
