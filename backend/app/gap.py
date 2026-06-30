"""Read-only applicant Gap Report (#9): which JD skills a resume doesn't show.

Given a chosen JD's requirements and a pasted resume, judge each JD skill and
report the gaps — skills the resume does not demonstrate (verdict "no") and
those it only partially demonstrates ("partial"). Derived from the same
per-skill judgments the scorer uses, but **informational only**: it persists
nothing (no Submission, no Evaluation) and never touches ranking.

The applicant flow is deliberately isolated (ADR-0003, Option B) so it can be
removed cleanly — hence its own module rather than living inside scoring.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.llm.gateway import LLMGateway
from app.llm.types import JDRequirements, SkillVerdict


class GapSkill(BaseModel):
    """One JD skill the resume falls short on (demonstrated skills are excluded)."""

    skill: str
    verdict: str  # "partial" | "no"
    kind: str  # "required" | "nice"


class GapReport(BaseModel):
    """Read-only summary of a resume's gaps against a JD's skills."""

    missing: list[GapSkill]  # verdict "no" — not demonstrated at all
    partial: list[GapSkill]  # verdict "partial" — only partially demonstrated
    demonstrated_count: int  # skills the resume does demonstrate ("yes")
    total_skills: int


def _verdict(gateway: LLMGateway, skill: str, resume_text: str) -> SkillVerdict:
    try:
        return gateway.judge_skill(skill, resume_text).verdict
    except Exception:  # unjudgeable (provider error): report as missing, never crash
        return SkillVerdict.NO


def build_gap_report(
    gateway: LLMGateway,
    requirements: JDRequirements,
    resume_text: str,
) -> GapReport:
    """Judge every JD skill against the resume and bucket the gaps. No I/O beyond
    the gateway; nothing is persisted."""
    skills = [("required", s) for s in requirements.required_skills]
    skills += [("nice", s) for s in requirements.nice_to_have_skills]

    missing: list[GapSkill] = []
    partial: list[GapSkill] = []
    demonstrated = 0

    for kind, skill in skills:
        verdict = _verdict(gateway, skill, resume_text)
        if verdict is SkillVerdict.YES:
            demonstrated += 1
        elif verdict is SkillVerdict.PARTIAL:
            partial.append(GapSkill(skill=skill, verdict=verdict.value, kind=kind))
        else:
            missing.append(GapSkill(skill=skill, verdict=verdict.value, kind=kind))

    return GapReport(
        missing=missing,
        partial=partial,
        demonstrated_count=demonstrated,
        total_skills=len(skills),
    )
