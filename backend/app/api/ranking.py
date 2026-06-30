"""Ranked candidates for a JD — what HR opens to see who fits best.

Reads stored Evaluations (computed on submission and refreshed when HR edits
the JD's requirements), so the dashboard renders instantly without a live model
call (story #19). Candidates are ordered best-match first; any not-yet-scored
submissions sort to the end.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Evaluation, JobDescription, Submission
from app.schemas import EvaluationRead, RankedCandidate

router = APIRouter(prefix="/api/jobs/{job_id}", tags=["ranking"])


def evaluation_read(evaluation: Evaluation | None) -> EvaluationRead | None:
    """Rebuild the API view of an Evaluation from its stored JSON columns."""
    if evaluation is None:
        return None
    return EvaluationRead(
        match_score=evaluation.match_score,
        components=evaluation.breakdown["components"],
        judgments=evaluation.judgments,
        weights=evaluation.weights,
    )


@router.get("/ranking", response_model=list[RankedCandidate])
def get_ranking(job_id: int, db: Session = Depends(get_db)) -> list[RankedCandidate]:
    if db.get(JobDescription, job_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="شرح شغل یافت نشد."
        )

    stmt = select(Submission).where(Submission.job_id == job_id)
    submissions = list(db.scalars(stmt).all())

    candidates = [
        RankedCandidate(
            submission_id=s.id,
            applicant_name=s.applicant_name,
            created_at=s.created_at,
            evaluation=evaluation_read(s.evaluation),
        )
        for s in submissions
    ]

    # Best match first. Unscored candidates (no evaluation) sort last; ties and
    # the unscored group fall back to newest-first.
    candidates.sort(key=lambda c: c.created_at, reverse=True)
    candidates.sort(
        key=lambda c: (
            c.evaluation is not None,
            c.evaluation.match_score if c.evaluation else 0.0,
        ),
        reverse=True,
    )
    return candidates
