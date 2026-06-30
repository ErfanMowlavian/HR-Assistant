"""Demo seed: load one Persian JD + resumes with pre-computed Evaluations.

Populates the database from the committed Gold Set (`app/eval/gold_set.json`)
so the HR dashboard renders a ranked list **instantly with no live model call**.
The Evaluations are computed once here with the deterministic `FakeLLMGateway`
and stored — so the demo runs even with the model provider unreachable, and the
seeded ranking has a clear, defensible top candidate (Issue #7).

    python -m app.seed     # (re)seed the demo JD + resumes + stored Evaluations
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal, init_db
from app.eval import GoldSet, load_gold_set
from app.llm.fake import FakeLLMGateway
from app.llm.gateway import LLMGateway
from app.models import JobDescription, Submission
from app.scoring import upsert_evaluation


def seed(
    db: Session,
    gateway: LLMGateway,
    gold: GoldSet | None = None,
) -> JobDescription:
    """Create the demo JD + submissions + stored Evaluations from the Gold Set.

    Idempotent on the demo JD: any existing JD with the same title (and its
    submissions/evaluations, via cascade) is removed first, so re-seeding gives
    a clean, reproducible state. Each submission is scored here and the result
    persisted, so the dashboard later ranks from stored data without a model call.
    """
    gold = gold or load_gold_set()

    existing = db.scalars(
        select(JobDescription).where(JobDescription.title == gold.job_title)
    ).all()
    for job in existing:
        db.delete(job)
    db.flush()

    job = JobDescription(
        title=gold.job_title,
        text=gold.job_text,
        requirements=gold.requirements.model_dump(),
    )
    db.add(job)
    db.flush()  # assign job.id

    for resume in gold.resumes:
        submission = Submission(
            job_id=job.id,
            applicant_name=resume.applicant_name,
            resume_text=resume.resume_text,
            resume_fields=resume.resume_fields.model_dump(),
        )
        db.add(submission)
        db.flush()  # assign submission.id before scoring
        upsert_evaluation(db, submission, job, gateway)

    db.commit()
    db.refresh(job)
    return job


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        # The fake gateway is deterministic and never touches the network, so
        # seeding works with the real provider unreachable.
        job = seed(db, FakeLLMGateway())
        count = len(job.submissions)
        print(f"Seeded demo JD «{job.title}» (#{job.id}) with {count} resumes + evaluations.")
        print("The HR dashboard ranks from stored data — no live model call needed.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
