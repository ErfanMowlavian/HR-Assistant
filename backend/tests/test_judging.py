"""The per-skill judging module (deepened seam).

This is the one home for "judge every JD skill, never crash" — so the
graceful-degradation behaviour is unit-tested here, not smeared across the
scorer and gap-report integration tests.
"""

from __future__ import annotations

from app.judging import judge_requirements
from app.llm.fake import FakeLLMGateway
from app.llm.gateway import LLMGateway
from app.llm.types import JDRequirements, SkillJudgment, SkillVerdict


def _reqs() -> JDRequirements:
    return JDRequirements(
        required_skills=["Python", "FastAPI"],
        nice_to_have_skills=["React"],
    )


def test_keeps_required_and_nice_split():
    judged = judge_requirements(FakeLLMGateway(), _reqs(), "مسلط به Python.")
    assert [j.skill for j in judged.required] == ["Python", "FastAPI"]
    assert [j.skill for j in judged.nice] == ["React"]


def test_tagged_pairs_each_judgment_with_its_kind():
    judged = judge_requirements(FakeLLMGateway(), _reqs(), "مسلط به Python.")
    tagged = judged.tagged()
    assert [(kind, j.skill) for kind, j in tagged] == [
        ("required", "Python"),
        ("required", "FastAPI"),
        ("nice", "React"),
    ]


def test_substring_fake_judges_present_skills_yes():
    judged = judge_requirements(FakeLLMGateway(), _reqs(), "مسلط به Python و FastAPI.")
    verdicts = {j.skill: j.verdict for _, j in judged.tagged()}
    assert verdicts["Python"] is SkillVerdict.YES
    assert verdicts["FastAPI"] is SkillVerdict.YES
    assert verdicts["React"] is SkillVerdict.NO


def test_provider_error_degrades_each_skill_to_no():
    class _Broken(LLMGateway):
        def extract_jd(self, text):  # pragma: no cover
            raise RuntimeError

        def extract_resume(self, text):  # pragma: no cover
            raise RuntimeError

        def judge_skill(self, skill: str, resume_text: str) -> SkillJudgment:
            raise RuntimeError("provider down")

    judged = judge_requirements(_Broken(), _reqs(), "متن")
    # A flaky model never crashes judging; every skill degrades to "no".
    assert all(j.verdict is SkillVerdict.NO for _, j in judged.tagged())
    # The failure cause is preserved on the judgment's reason.
    assert all("provider down" in (j.reason or "") for _, j in judged.tagged())


def test_empty_requirements_judge_to_empty_groups():
    judged = judge_requirements(FakeLLMGateway(), JDRequirements(), "متن")
    assert judged.required == []
    assert judged.nice == []
    assert judged.tagged() == []
