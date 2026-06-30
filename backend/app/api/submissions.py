"""Submission endpoints: an applicant applies to a JD by pasting a resume."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_gateway
from app.extraction import extract_resume_fields
from app.extraction.pdf import PdfExtractionError, extract_pdf_text, looks_garbled
from app.llm.errors import GatewayError
from app.llm.gateway import LLMGateway
from app.models import JobDescription, Submission
from app.schemas import SubmissionCreate, SubmissionRead
from app.scoring import evaluate_submission, store_outcome

router = APIRouter(prefix="/api/jobs/{job_id}/submissions", tags=["submissions"])

# Shown when a PDF extracts to broken/garbled text. Paste is the reliable path.
PASTE_NUDGE = (
    "متن قابل‌استفاده‌ای از این PDF استخراج نشد (خروجی ناقص یا درهم‌ریخته بود). "
    "لطفاً به‌جای آپلود، متن رزومه را مستقیماً وارد کنید."
)


def _job_or_404(db: Session, job_id: int) -> JobDescription:
    job = db.get(JobDescription, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="شرح شغل یافت نشد.")
    return job


def _create_submission(
    db: Session,
    job: JobDescription,
    gateway: LLMGateway,
    *,
    applicant_name: str,
    resume_text: str,
) -> Submission:
    """Create + extract + score one Submission. Shared by paste and PDF upload,
    so an uploaded resume travels the exact same path as a pasted one.

    All LLM work (extraction + per-skill judging) happens *before* the write
    transaction is opened. SQLite allows only one writer at a time, so holding
    the write lock across these multi-second network calls would serialize
    concurrent applicants into "database is locked" 500s. Computing first, then
    writing in a quick burst, keeps the lock held for milliseconds.
    """
    submission = Submission(
        job_id=job.id,
        applicant_name=applicant_name,
        resume_text=resume_text,
    )

    # Extract structured fields, reusing the extraction infra. As with JD
    # extraction, a failed/unreachable model doesn't lose the resume: the
    # Submission is persisted with resume_fields=null and flagged.
    try:
        fields = extract_resume_fields(gateway, resume_text)
        submission.resume_fields = fields.model_dump()
    except GatewayError:
        submission.resume_fields = None

    # Score against the JD (story #11) so HR's ranked view is ready from stored
    # results. The judging (LLM) runs here, outside any transaction; the no-op
    # case (JD has no requirements yet) returns None.
    outcome = evaluate_submission(gateway, submission, job)

    # --- Short write transaction: no network I/O past this point. ---
    db.add(submission)
    db.flush()  # assign submission.id for the Evaluation FK
    if outcome is not None:
        store_outcome(db, submission, outcome)
    db.commit()
    db.refresh(submission)
    return submission


@router.post("", response_model=SubmissionRead, status_code=status.HTTP_201_CREATED)
def create_submission(
    job_id: int,
    payload: SubmissionCreate,
    db: Session = Depends(get_db),
    gateway: LLMGateway = Depends(get_gateway),
) -> Submission:
    job = _job_or_404(db, job_id)
    return _create_submission(
        db,
        job,
        gateway,
        applicant_name=payload.applicant_name,
        resume_text=payload.resume_text,
    )


@router.post("/upload", response_model=SubmissionRead, status_code=status.HTTP_201_CREATED)
async def upload_submission(
    job_id: int,
    applicant_name: str = Form(min_length=1, max_length=255),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    gateway: LLMGateway = Depends(get_gateway),
) -> Submission:
    """Best-effort PDF upload (#8): an alternative to pasting.

    The PDF is parsed with pypdf and the extracted text feeds the same
    Submission path as pasted text. If extraction fails or the text looks
    garbled, we refuse with a 422 nudge to paste instead — so a broken PDF can
    never silently produce a corrupted Evaluation.
    """
    job = _job_or_404(db, job_id)

    data = await file.read()
    try:
        text = extract_pdf_text(data)
    except PdfExtractionError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=PASTE_NUDGE
        )

    if looks_garbled(text):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=PASTE_NUDGE
        )

    return _create_submission(
        db, job, gateway, applicant_name=applicant_name, resume_text=text
    )


@router.get("", response_model=list[SubmissionRead])
def list_submissions(job_id: int, db: Session = Depends(get_db)) -> list[Submission]:
    _job_or_404(db, job_id)
    stmt = (
        select(Submission)
        .where(Submission.job_id == job_id)
        .order_by(Submission.created_at.desc())
    )
    return list(db.scalars(stmt).all())
