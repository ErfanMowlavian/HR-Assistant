"""Typed payloads exchanged with the LLM gateway (Pydantic v2).

These schemas are what Instructor constrains the model output to in later
slices (#3 JD extraction, #4 resume extraction, #5 per-skill judgment). They
live here so every layer shares one vocabulary (docs/glossary.md).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class JDRequirements(BaseModel):
    """Structured requirements extracted from a Job Description."""

    required_skills: list[str] = Field(default_factory=list)
    nice_to_have_skills: list[str] = Field(default_factory=list)
    min_years_experience: int = 0
    education: str | None = None
    seniority: str | None = None


class ResumeFields(BaseModel):
    """Structured fields extracted from a resume."""

    skills: list[str] = Field(default_factory=list)
    total_years_experience: float = 0.0
    titles: list[str] = Field(default_factory=list)
    education: str | None = None


class SkillVerdict(str, Enum):
    """The LLM's verdict for one required skill against one resume."""

    YES = "yes"
    PARTIAL = "partial"
    NO = "no"


class SkillJudgment(BaseModel):
    """Per-skill judgment; aggregated by the deterministic scorer (ADR-0002)."""

    skill: str
    verdict: SkillVerdict
    reason: str | None = None
