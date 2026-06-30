"""A deterministic fake gateway for tests and offline development.

Returns canned, schema-valid results with no network call, so the whole app is
testable without a real model (PRD "Seam 1", story #24). Canned values can be
overridden per-instance for tests that need specific extractions/judgments.
"""

from __future__ import annotations

from app.llm.gateway import LLMGateway
from app.llm.types import (
    JDRequirements,
    ResumeFields,
    SkillJudgment,
    SkillVerdict,
)


class FakeLLMGateway(LLMGateway):
    def __init__(
        self,
        *,
        jd: JDRequirements | None = None,
        resume: ResumeFields | None = None,
        judgment: SkillJudgment | None = None,
    ) -> None:
        self._jd = jd or JDRequirements(
            required_skills=["Python", "FastAPI"],
            nice_to_have_skills=["React"],
            min_years_experience=3,
            education="کارشناسی",
            seniority="senior",
        )
        self._resume = resume or ResumeFields(
            skills=["Python", "FastAPI", "SQL"],
            total_years_experience=5.0,
            titles=["مهندس نرم‌افزار"],
            education="کارشناسی",
        )
        self._judgment = judgment

    def extract_jd(self, text: str) -> JDRequirements:
        return self._jd

    def extract_resume(self, text: str) -> ResumeFields:
        return self._resume

    def judge_skill(self, skill: str, resume_text: str) -> SkillJudgment:
        if self._judgment is not None:
            return self._judgment
        verdict = (
            SkillVerdict.YES
            if skill.lower() in resume_text.lower()
            else SkillVerdict.NO
        )
        return SkillJudgment(skill=skill, verdict=verdict)
