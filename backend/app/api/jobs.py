"""Job Description endpoints: create (with requirement extraction), list,
get one, and review/correct the extracted requirements."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_gateway
from app.extraction import extract_jd_requirements
from app.llm.errors import GatewayError
from app.llm.gateway import LLMGateway
from app.models import JobDescription
from app.schemas import JobDescriptionCreate, JobDescriptionRead, RequirementsUpdate
from app.scoring import upsert_evaluation

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _get_or_404(db: Session, job_id: int) -> JobDescription:
    job = db.get(JobDescription, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="شرح شغل یافت نشد.")
    return job


@router.post("", response_model=JobDescriptionRead, status_code=status.HTTP_201_CREATED)
def create_job(
    payload: JobDescriptionCreate,
    db: Session = Depends(get_db),
    gateway: LLMGateway = Depends(get_gateway),
) -> JobDescription:
    job = JobDescription(title=payload.title, text=payload.text)

    # Creating a JD triggers schema-constrained extraction of its requirements.
    # If the model is unreachable or returns junk, we still persist the JD
    # (requirements stay null) so the text is never lost and HR can fill them
    # in or re-run extraction. The JD is not held hostage by a flaky model.
    try:
        requirements = extract_jd_requirements(gateway, payload.text)
        job.requirements = requirements.model_dump()
    except GatewayError:
        job.requirements = None

    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("", response_model=list[JobDescriptionRead])
def list_jobs(db: Session = Depends(get_db)) -> list[JobDescription]:
    stmt = select(JobDescription).order_by(JobDescription.created_at.desc())
    return list(db.scalars(stmt).all())


@router.get("/{job_id}", response_model=JobDescriptionRead)
def get_job(job_id: int, db: Session = Depends(get_db)) -> JobDescription:
    return _get_or_404(db, job_id)


@router.patch("/{job_id}/requirements", response_model=JobDescriptionRead)
def update_requirements(
    job_id: int,
    payload: RequirementsUpdate,
    db: Session = Depends(get_db),
    gateway: LLMGateway = Depends(get_gateway),
) -> JobDescription:
    """HR reviews and corrects the extracted requirements before they're used.

    The payload is validated against the JDRequirements schema, so a bad edit
    can't silently corrupt the ranking inputs. Correcting the requirements
    changes what every candidate is scored against, so each of the JD's
    submissions is re-evaluated against the new requirements.
    """
    job = _get_or_404(db, job_id)
    job.requirements = payload.model_dump()
    db.add(job)
    db.flush()

    for submission in job.submissions:
        upsert_evaluation(db, submission, job, gateway)

    db.commit()
    db.refresh(job)
    return job
