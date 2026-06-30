"""Ranked candidates for a JD — what HR opens to see who fits best.

Reads stored Evaluations (computed on submission and refreshed when HR edits
the JD's requirements), so the dashboard renders instantly without a live model
call (story #19). Candidates are ordered best-match first; any not-yet-scored
submissions sort to the end.

`POST /rank` ("rank now") re-runs the scoring pipeline live for every
submission of a JD — the on-demand proof that the pipeline works, separate from
the stored-data read path (Issue #7).
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.api.submissions import rescore_job_in_background
from app.db import get_db, get_sessionmaker
from app.deps import get_gateway
from app.llm.gateway import LLMGateway
from app.models import JobDescription, Submission
from app.schemas import EvaluationRead, RankedCandidate

router = APIRouter(prefix="/api/jobs/{job_id}", tags=["ranking"])


def _job_or_404(db: Session, job_id: int) -> JobDescription:
    job = db.get(JobDescription, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="شرح شغل یافت نشد."
        )
    return job


def _ranked(db: Session, job_id: int) -> list[RankedCandidate]:
    """Build the best-match-first candidate list from stored Evaluations."""
    stmt = select(Submission).where(Submission.job_id == job_id)
    submissions = list(db.scalars(stmt).all())

    candidates = [
        RankedCandidate(
            submission_id=s.id,
            applicant_name=s.applicant_name,
            status=s.status,
            created_at=s.created_at,
            evaluation=(
                EvaluationRead.from_evaluation(s.evaluation) if s.evaluation else None
            ),
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


@router.get("/ranking", response_model=list[RankedCandidate])
def get_ranking(job_id: int, db: Session = Depends(get_db)) -> list[RankedCandidate]:
    # No gateway dependency: this path only reads stored Evaluations, so the
    # dashboard renders even with the model provider unreachable (Issue #7).
    _job_or_404(db, job_id)
    return _ranked(db, job_id)


@router.post("/rank", response_model=list[RankedCandidate])
def rank_now(
    job_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    gateway: LLMGateway = Depends(get_gateway),
    session_factory: sessionmaker = Depends(get_sessionmaker),
) -> list[RankedCandidate]:
    """Re-run the scoring pipeline live for every submission of a JD.

    Re-judging every skill of every candidate is many model calls (tens of
    seconds), which would exceed a reverse proxy's timeout. So this marks the
    candidates "processing", kicks off the re-score in the background
    (ADR-0013), and returns the current ranking immediately; the dashboard polls
    until each row settles. A no-op per submission when the JD has no
    requirements.
    """
    job = _job_or_404(db, job_id)
    for submission in job.submissions:
        submission.status = "processing"
    db.commit()

    background_tasks.add_task(rescore_job_in_background, session_factory, gateway, job.id)
    return _ranked(db, job_id)
