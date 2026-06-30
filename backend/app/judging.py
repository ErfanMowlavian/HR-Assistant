"""Per-skill judging: ask the gateway to judge each JD skill against a resume.

One home for "judge every required + nice-to-have skill, never crash". The LLM
produces a per-skill verdict (yes/partial/no, ADR-0002); a provider error
degrades that one skill to "no" rather than failing the whole judgment — a
flaky model lowers a score, it never crashes the pipeline.

Both the scorer (`scoring.service`) and the applicant Gap Report (`gap`) consume
this. It depends only on the gateway seam and the shared types, so the two
consumers stay decoupled from each other — removing the Gap Report (ADR-0003,
Option B) touches neither this module nor scoring.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.llm.gateway import LLMGateway
from app.llm.types import JDRequirements, SkillJudgment, SkillVerdict


@dataclass(frozen=True)
class JudgedRequirements:
    """Per-skill judgments for one resume, keeping the required/nice split the
    deterministic scorer needs."""

    required: list[SkillJudgment]
    nice: list[SkillJudgment]

    def tagged(self) -> list[tuple[str, SkillJudgment]]:
        """Each judgment paired with its requirement kind ("required"|"nice").

        The single place callers walk both groups — the flat persistence
        projection and the gap-report buckets both iterate this.
        """
        return [("required", j) for j in self.required] + [
            ("nice", j) for j in self.nice
        ]


def _judge(gateway: LLMGateway, skill: str, resume_text: str) -> SkillJudgment:
    try:
        return gateway.judge_skill(skill, resume_text)
    except Exception as exc:  # provider error: treat as unmet, never crash
        return SkillJudgment(skill=skill, verdict=SkillVerdict.NO, reason=str(exc))


def judge_requirements(
    gateway: LLMGateway,
    requirements: JDRequirements,
    resume_text: str,
) -> JudgedRequirements:
    """Judge every required and nice-to-have skill against the resume."""
    return JudgedRequirements(
        required=[_judge(gateway, s, resume_text) for s in requirements.required_skills],
        nice=[_judge(gateway, s, resume_text) for s in requirements.nice_to_have_skills],
    )
