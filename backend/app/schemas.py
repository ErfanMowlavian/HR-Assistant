"""Pydantic v2 request/response schemas for the HTTP API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.llm.types import JDRequirements, ResumeFields
from app.scoring.scorer import ComponentScore
from app.scoring.weights import ScoreWeights


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


class SubmissionCreate(BaseModel):
    """Payload an applicant sends to apply to a JD."""

    applicant_name: str = Field(min_length=1, max_length=255)
    resume_text: str = Field(min_length=1, description="The full Persian resume text.")


class SubmissionRead(BaseModel):
    """A Submission as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    job_id: int
    applicant_name: str
    resume_text: str
    resume_fields: ResumeFields | None = None
    created_at: datetime

    @computed_field
    @property
    def extraction_ok(self) -> bool:
        return self.resume_fields is not None


class SkillJudgmentRead(BaseModel):
    """One per-skill judgment as shown to HR: which requirement, and the verdict."""

    skill: str
    verdict: str  # "yes" | "partial" | "no"
    reason: str | None = None
    kind: str  # "required" | "nice"


class EvaluationRead(BaseModel):
    """A Submission's Evaluation: Match Score, breakdown, per-skill judgments."""

    match_score: float
    components: list[ComponentScore]
    judgments: list[SkillJudgmentRead]
    weights: ScoreWeights


class GapReportRequest(BaseModel):
    """Applicant payload for a read-only gap report: just their resume text.

    No display name and no persistence — the report is informational only and
    creates neither a Submission nor an Evaluation (Issue #9)."""

    resume_text: str = Field(min_length=1, description="The resume text to check.")


class RankedCandidate(BaseModel):
    """One row in a JD's ranked candidate list.

    `evaluation` is null for submissions not yet scored (e.g. the JD had no
    extracted requirements when they applied); those sort after scored ones.
    """

    submission_id: int
    applicant_name: str
    created_at: datetime
    evaluation: EvaluationRead | None = None
