"""Job Description endpoints: create and list (the walking skeleton's flow)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import JobDescription
from app.schemas import JobDescriptionCreate, JobDescriptionRead

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("", response_model=JobDescriptionRead, status_code=status.HTTP_201_CREATED)
def create_job(payload: JobDescriptionCreate, db: Session = Depends(get_db)) -> JobDescription:
    job = JobDescription(title=payload.title, text=payload.text)
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("", response_model=list[JobDescriptionRead])
def list_jobs(db: Session = Depends(get_db)) -> list[JobDescription]:
    stmt = select(JobDescription).order_by(JobDescription.created_at.desc())
    return list(db.scalars(stmt).all())
