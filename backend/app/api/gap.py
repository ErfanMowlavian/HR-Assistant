"""Read-only applicant Gap Report endpoint (Issue #9).

`POST /api/jobs/{id}/gap-report` takes a pasted resume and returns the JD skills
it doesn't demonstrate. It only reads the JD and calls the gateway — it writes
nothing, so generating a gap report never changes any Evaluation or ranking.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_gateway
from app.gap import GapReport, build_gap_report
from app.llm.gateway import LLMGateway
from app.llm.types import JDRequirements
from app.models import JobDescription
from app.schemas import GapReportRequest

router = APIRouter(prefix="/api/jobs/{job_id}", tags=["gap-report"])


@router.post("/gap-report", response_model=GapReport)
def get_gap_report(
    job_id: int,
    payload: GapReportRequest,
    db: Session = Depends(get_db),
    gateway: LLMGateway = Depends(get_gateway),
) -> GapReport:
    job = db.get(JobDescription, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="شرح شغل یافت نشد."
        )
    if not job.requirements:
        # Nothing to compare against yet — the JD's requirements aren't ready.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="مهارت‌های این آگهی هنوز مشخص نشده‌اند.",
        )

    requirements = JDRequirements.model_validate(job.requirements)
    # Read-only: no db.add / db.commit anywhere in this path.
    return build_gap_report(gateway, requirements, payload.resume_text)
