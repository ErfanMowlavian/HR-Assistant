"""Submission endpoints: an applicant applies to a JD by pasting/uploading a
resume.

Scoring is asynchronous (ADR-0013): the resume is saved and a 201 returns
immediately with status="processing", then the slow LLM work (extraction +
per-skill judging, ~tens of seconds on a real model) runs in a background task
that updates the row to "done". Applicants never block on the model, and the
request never outlives a reverse proxy's timeout. The UI polls the submission
until it leaves "processing".
"""

from __future__ import annotations

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.db import get_db, get_sessionmaker
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


def _create_pending_submission(
    db: Session,
    job: JobDescription,
    *,
    applicant_name: str,
    resume_text: str,
) -> Submission:
    """Persist the raw resume immediately as a "processing" Submission.

    No LLM call here — just a quick write — so the applicant gets an instant
    201. Extraction and scoring happen later in `score_submission`.
    """
    submission = Submission(
        job_id=job.id,
        applicant_name=applicant_name,
        resume_text=resume_text,
        status="processing",
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission


def score_submission(
    session_factory: sessionmaker,
    gateway: LLMGateway,
    submission_id: int,
) -> None:
    """Background worker: extract + judge + score one submission, then mark it
    "done" ("failed" on an unexpected error).

    Runs after the response is sent, so the applicant never waits on the model.
    Opens its own session (the request's is already closed). As in the sync
    path, all LLM I/O happens before the write, so the SQLite write lock is held
    only for the final quick commit (ADR-0012). A provider error during
    extraction degrades to resume_fields=null; a per-skill judging error
    degrades that skill to "no" — neither fails the submission.
    """
    db = session_factory()
    try:
        submission = db.get(Submission, submission_id)
        if submission is None:  # deleted before scoring ran
            return
        job = db.get(JobDescription, submission.job_id)

        try:
            fields = extract_resume_fields(gateway, submission.resume_text)
            submission.resume_fields = fields.model_dump()
        except GatewayError:
            submission.resume_fields = None

        outcome = evaluate_submission(gateway, submission, job) if job else None

        # --- Short write transaction: no network I/O past this point. ---
        if outcome is not None:
            store_outcome(db, submission, outcome)
        submission.status = "done"
        db.commit()
    except Exception:
        # Unexpected (non-gateway) failure: flag it so the UI stops polling and
        # can show an error, rather than spinning forever on "processing".
        db.rollback()
        submission = db.get(Submission, submission_id)
        if submission is not None:
            submission.status = "failed"
            db.commit()
    finally:
        db.close()


@router.post("", response_model=SubmissionRead, status_code=status.HTTP_201_CREATED)
def create_submission(
    job_id: int,
    payload: SubmissionCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    gateway: LLMGateway = Depends(get_gateway),
    session_factory: sessionmaker = Depends(get_sessionmaker),
) -> Submission:
    job = _job_or_404(db, job_id)
    submission = _create_pending_submission(
        db, job, applicant_name=payload.applicant_name, resume_text=payload.resume_text
    )
    background_tasks.add_task(score_submission, session_factory, gateway, submission.id)
    return submission


@router.post("/upload", response_model=SubmissionRead, status_code=status.HTTP_201_CREATED)
async def upload_submission(
    job_id: int,
    background_tasks: BackgroundTasks,
    applicant_name: str = Form(min_length=1, max_length=255),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    gateway: LLMGateway = Depends(get_gateway),
    session_factory: sessionmaker = Depends(get_sessionmaker),
) -> Submission:
    """Best-effort PDF upload (#8): an alternative to pasting.

    The PDF is parsed with pypdf and the extracted text feeds the same async
    Submission path as pasted text. If extraction fails or the text looks
    garbled, we refuse with a 422 nudge to paste instead — so a broken PDF can
    never silently produce a corrupted Evaluation. The PDF parse is fast and
    happens here; only the LLM scoring is deferred to the background.
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

    submission = _create_pending_submission(
        db, job, applicant_name=applicant_name, resume_text=text
    )
    background_tasks.add_task(score_submission, session_factory, gateway, submission.id)
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


@router.get("/{submission_id}", response_model=SubmissionRead)
def get_submission(
    job_id: int, submission_id: int, db: Session = Depends(get_db)
) -> Submission:
    """Fetch one submission — the endpoint the apply page polls to watch
    `status` move from "processing" to "done"."""
    _job_or_404(db, job_id)
    submission = db.get(Submission, submission_id)
    if submission is None or submission.job_id != job_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="رزومه یافت نشد.")
    return submission
