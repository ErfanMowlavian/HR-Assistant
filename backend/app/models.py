"""ORM models. Terms match docs/glossary.md (Job Description, Submission, …).

The walking skeleton only needs the Job Description entity. Submission and
Evaluation arrive in later slices (#4, #5).
"""

from __future__ import annotations

from datetime import datetime, timezone

from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class JobDescription(Base):
    """A role definition written by HR; resumes are ranked against it."""

    __tablename__ = "job_descriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    # Structured requirements extracted from `text` (LLM-extracted, then
    # HR-reviewable). Null until extraction succeeds. Shape: JDRequirements.
    requirements: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    submissions: Mapped[list["Submission"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class Submission(Base):
    """One applicant's resume sent against one chosen JD."""

    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("job_descriptions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    applicant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Raw resume text, stored verbatim so mixed Persian/English skill text is
    # preserved for later per-skill judgment (#5).
    resume_text: Mapped[str] = mapped_column(Text, nullable=False)
    # Structured fields extracted from the resume. Null until extraction
    # succeeds. Shape: ResumeFields.
    resume_fields: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    job: Mapped["JobDescription"] = relationship(back_populates="submissions")
