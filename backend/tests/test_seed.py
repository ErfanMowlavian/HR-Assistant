"""Demo seed (Issue #7): one Persian JD + resumes with pre-computed Evaluations.

The seed loads the committed Gold Set and stores an Evaluation per submission,
so the HR dashboard ranks from stored data with no live model call. The fake
gateway is deterministic and never networks, so seeding works with the real
provider unreachable.
"""

from __future__ import annotations

from app.llm.gateway import LLMGateway
from app.llm.types import SkillJudgment, SkillVerdict
from app.seed import seed


class _UnreachableGateway(LLMGateway):
    """Stands in for the model provider being down: judging always fails."""

    def extract_jd(self, text):  # pragma: no cover - not used by seed
        raise RuntimeError("provider unreachable")

    def extract_resume(self, text):  # pragma: no cover - not used by seed
        raise RuntimeError("provider unreachable")

    def judge_skill(self, skill: str, resume_text: str) -> SkillJudgment:
        raise RuntimeError("provider unreachable")


def test_seed_populates_jd_resumes_and_evaluations(db_session):
    from app.llm.fake import FakeLLMGateway

    job = seed(db_session, FakeLLMGateway())

    assert job.requirements["required_skills"]  # JD seeded with requirements
    assert len(job.submissions) >= 8  # ADR-0003: ~8 resumes
    # Every seeded submission has a stored Evaluation, so the dashboard renders
    # the ranked list from stored data without any live call.
    assert all(s.evaluation is not None for s in job.submissions)
    assert all(s.resume_fields is not None for s in job.submissions)


def test_seeded_ranking_has_a_clear_defensible_top(db_session):
    from app.llm.fake import FakeLLMGateway

    job = seed(db_session, FakeLLMGateway())
    ranked = sorted(
        job.submissions, key=lambda s: s.evaluation.match_score, reverse=True
    )
    # The Gold Set's strongest candidate (all skills, most experience, دکتری).
    assert ranked[0].applicant_name == "سارا محمدی"
    assert ranked[0].evaluation.match_score > ranked[1].evaluation.match_score


def test_seed_is_idempotent(db_session):
    from app.llm.fake import FakeLLMGateway

    first = seed(db_session, FakeLLMGateway())
    n = len(first.submissions)
    second = seed(db_session, FakeLLMGateway())

    # Re-seeding replaces the demo JD rather than duplicating it.
    from app.models import JobDescription, Submission

    assert db_session.query(JobDescription).count() == 1
    assert db_session.query(Submission).count() == n
    assert len(second.submissions) == n


def test_seed_works_with_provider_unreachable(db_session):
    # Seeding must not depend on a live model. With every judgment failing, the
    # pipeline degrades each skill to "no" but still stores an Evaluation —
    # the demo is populated and rankable offline.
    job = seed(db_session, _UnreachableGateway())

    assert len(job.submissions) >= 8
    assert all(s.evaluation is not None for s in job.submissions)
    # All skills judged "no" → required/nice coverage is zero for everyone.
    for s in job.submissions:
        verdicts = {j["verdict"] for j in s.evaluation.judgments}
        assert verdicts <= {SkillVerdict.NO.value}
