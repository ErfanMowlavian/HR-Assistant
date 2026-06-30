"""Pure unit tests for the applicant Gap Report builder (Issue #9)."""

from __future__ import annotations

from app.gap import build_gap_report
from app.llm.fake import FakeLLMGateway
from app.llm.gateway import LLMGateway
from app.llm.types import JDRequirements, SkillJudgment, SkillVerdict


def _reqs() -> JDRequirements:
    return JDRequirements(
        required_skills=["Python", "FastAPI"],
        nice_to_have_skills=["React"],
        min_years_experience=3,
        education="کارشناسی",
        seniority="senior",
    )


def test_missing_skills_are_those_not_demonstrated():
    # Substring fake: the resume names only Python.
    report = build_gap_report(FakeLLMGateway(), _reqs(), "مسلط به Python.")

    missing = {g.skill for g in report.missing}
    assert missing == {"FastAPI", "React"}
    assert report.demonstrated_count == 1  # Python
    assert report.total_skills == 3
    # Each gap carries which kind of requirement it was.
    kinds = {g.skill: g.kind for g in report.missing}
    assert kinds == {"FastAPI": "required", "React": "nice"}


def test_partial_verdicts_are_reported_separately():
    gateway = FakeLLMGateway(
        judgments={
            "Python": SkillVerdict.YES,
            "FastAPI": SkillVerdict.PARTIAL,
            "React": SkillVerdict.NO,
        }
    )
    report = build_gap_report(gateway, _reqs(), "هر متنی")

    assert {g.skill for g in report.partial} == {"FastAPI"}
    assert {g.skill for g in report.missing} == {"React"}
    assert report.demonstrated_count == 1


def test_fully_qualified_resume_has_no_gaps():
    gateway = FakeLLMGateway(judgment=SkillJudgment(skill="x", verdict=SkillVerdict.YES))
    report = build_gap_report(gateway, _reqs(), "مسلط به همه‌چیز.")

    assert report.missing == []
    assert report.partial == []
    assert report.demonstrated_count == report.total_skills == 3


def test_unjudgeable_skill_degrades_to_missing():
    class _Broken(LLMGateway):
        def extract_jd(self, text):  # pragma: no cover
            raise RuntimeError

        def extract_resume(self, text):  # pragma: no cover
            raise RuntimeError

        def judge_skill(self, skill, resume_text):
            raise RuntimeError("provider down")

    report = build_gap_report(_Broken(), _reqs(), "متن")
    # A flaky model never crashes the report; the skill shows as missing.
    assert {g.skill for g in report.missing} == {"Python", "FastAPI", "React"}
    assert report.demonstrated_count == 0
