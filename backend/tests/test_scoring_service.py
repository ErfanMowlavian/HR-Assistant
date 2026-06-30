"""The evaluation orchestrators (upsert_evaluation / rescore_job) — direct.

These were previously reachable only through HTTP round-trips. Here they're
exercised against an in-memory DB + fake gateway, so the orchestration logic
(validate → judge → score → persist, one Evaluation per Submission) is the test
surface, not the routers.
"""

from __future__ import annotations

import pytest

from app.llm.fake import FakeLLMGateway
from app.models import JobDescription, Submission
from app.scoring import rescore_job, upsert_evaluation


def _job(db, *, with_requirements: bool) -> JobDescription:
    job = JobDescription(
        title="بک‌اند",
        text="متن",
        requirements=(
            {
                "required_skills": ["Python", "FastAPI"],
                "nice_to_have_skills": ["React"],
                "min_years_experience": 0,
                "education": None,
                "seniority": None,
            }
            if with_requirements
            else None
        ),
    )
    db.add(job)
    db.flush()
    return job


def _submit(db, job, name: str, resume: str) -> Submission:
    s = Submission(job_id=job.id, applicant_name=name, resume_text=resume)
    db.add(s)
    db.flush()
    return s


def test_upsert_evaluation_scores_and_persists_one_evaluation(db_session):
    job = _job(db_session, with_requirements=True)
    s = _submit(db_session, job, "قوی", "مسلط به Python و FastAPI و React.")

    ev = upsert_evaluation(db_session, s, job, FakeLLMGateway())
    assert ev is not None
    assert s.evaluation is ev
    assert ev.match_score == pytest.approx(1.0)  # all skills judged yes


def test_upsert_evaluation_is_a_noop_without_requirements(db_session):
    job = _job(db_session, with_requirements=False)
    s = _submit(db_session, job, "نامزد", "متن")

    assert upsert_evaluation(db_session, s, job, FakeLLMGateway()) is None
    assert s.evaluation is None


def test_upsert_evaluation_replaces_in_place_when_rerun(db_session):
    job = _job(db_session, with_requirements=True)
    s = _submit(db_session, job, "نامزد", "مسلط به Python.")

    first = upsert_evaluation(db_session, s, job, FakeLLMGateway())
    second = upsert_evaluation(db_session, s, job, FakeLLMGateway())
    # One Evaluation per Submission — re-running updates, never duplicates.
    assert first is second


def test_rescore_job_scores_every_submission(db_session):
    job = _job(db_session, with_requirements=True)
    weak = _submit(db_session, job, "ضعیف", "بدون فناوری خاص.")
    strong = _submit(db_session, job, "قوی", "مسلط به Python و FastAPI و React.")

    evaluations = rescore_job(db_session, job, FakeLLMGateway())

    assert len(evaluations) == 2
    assert weak.evaluation is not None and strong.evaluation is not None
    assert strong.evaluation.match_score > weak.evaluation.match_score


def test_rescore_job_skips_unscored_when_no_requirements(db_session):
    job = _job(db_session, with_requirements=False)
    _submit(db_session, job, "نامزد", "متن")

    assert rescore_job(db_session, job, FakeLLMGateway()) == []
