"""Submission endpoints: an applicant applies to a JD by pasting a resume."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_gateway
from app.extraction import extract_resume_fields
from app.extraction.service import ExtractionError
from app.llm.gateway import LLMGateway
from app.models import JobDescription, Submission
from app.schemas import SubmissionCreate, SubmissionRead

router = APIRouter(prefix="/api/jobs/{job_id}/submissions", tags=["submissions"])


def _job_or_404(db: Session, job_id: int) -> JobDescription:
    job = db.get(JobDescription, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="شرح شغل یافت نشد.")
    return job


@router.post("", response_model=SubmissionRead, status_code=status.HTTP_201_CREATED)
def create_submission(
    job_id: int,
    payload: SubmissionCreate,
    db: Session = Depends(get_db),
    gateway: LLMGateway = Depends(get_gateway),
) -> Submission:
    _job_or_404(db, job_id)

    submission = Submission(
        job_id=job_id,
        applicant_name=payload.applicant_name,
        resume_text=payload.resume_text,
    )

    # Extract structured fields on submission, reusing the extraction infra.
    # As with JD extraction, a failed/unreachable model doesn't lose the
    # resume: the Submission is persisted with resume_fields=null and flagged.
    try:
        fields = extract_resume_fields(gateway, payload.resume_text)
        submission.resume_fields = fields.model_dump()
    except ExtractionError:
        submission.resume_fields = None

    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission


@router.get("", response_model=list[SubmissionRead])
def list_submissions(job_id: int, db: Session = Depends(get_db)) -> list[Submission]:
    _job_or_404(db, job_id)
    stmt = (
        select(Submission)
        .where(Submission.job_id == job_id)
        .order_by(Submission.created_at.desc())
    )
    return list(db.scalars(stmt).all())
