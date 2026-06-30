"""The deterministic scorer — a pure function (PRD "Seam 2").

`score()` takes JD requirements, the per-skill judgments the LLM produced, the
extracted resume fields, and the weights, and returns a Match Score in [0, 1]
plus a per-criterion breakdown. No I/O, no model call, no randomness: the same
inputs always yield the same ranking, which is what makes the ranking auditable
(ADR-0002). The LLM reads; this function judges.

Skill matching is *not* string matching here: each skill already carries an
LLM verdict (yes / partial / no) that treats Persian and English variants of a
skill as the same (e.g. "React" == "ری‌اکت"). This function only aggregates
those verdicts, so synonym handling is correct by construction.
"""

from __future__ import annotations

from pydantic import BaseModel

from app.llm.types import JDRequirements, ResumeFields, SkillJudgment, SkillVerdict
from app.normalize import normalize_digits
from app.scoring.weights import ScoreWeights

# A verdict's contribution to coverage. "partial" counts as half credit.
_VERDICT_VALUE: dict[SkillVerdict, float] = {
    SkillVerdict.YES: 1.0,
    SkillVerdict.PARTIAL: 0.5,
    SkillVerdict.NO: 0.0,
}

# Ordinal ranking of education levels (Persian first, common English/synonyms
# folded in). A resume at or above the required level fully satisfies it; a
# lower-but-present level earns half credit.
_EDUCATION_RANK: dict[str, int] = {
    "دیپلم": 1,
    "کاردانی": 2,
    "فوق دیپلم": 2,
    "کارشناسی": 3,
    "لیسانس": 3,
    "bachelor": 3,
    "کارشناسی ارشد": 4,
    "فوق لیسانس": 4,
    "master": 4,
    "دکتری": 5,
    "دکترا": 5,
    "phd": 5,
    "doctorate": 5,
}


def _education_rank(value: str | None) -> int | None:
    """Map an education string to an ordinal level, or None if unrecognized."""
    if not value:
        return None
    key = normalize_digits(value).strip().lower()
    if key in _EDUCATION_RANK:
        return _EDUCATION_RANK[key]
    # Tolerate extra words around a known level (e.g. "کارشناسی کامپیوتر").
    for term, rank in _EDUCATION_RANK.items():
        if term in key:
            return rank
    return None


class ComponentScore(BaseModel):
    """One criterion's contribution to the Match Score (explainability)."""

    key: str
    label: str
    applicable: bool
    score: float | None  # raw criterion score in [0, 1]; None when N/A
    weight: float
    contribution: float  # normalized share of the final Match Score


class ScoreResult(BaseModel):
    """The Match Score and the breakdown that justifies it."""

    match_score: float
    components: list[ComponentScore]


def _coverage(judgments: list[SkillJudgment]) -> float:
    """Mean verdict value over a skill set, in [0, 1]."""
    if not judgments:
        return 0.0
    total = sum(_VERDICT_VALUE[j.verdict] for j in judgments)
    return total / len(judgments)


def _experience_score(min_years: int, resume_years: float) -> float:
    """Fraction of the required experience met, capped at 1.0."""
    if min_years <= 0:
        return 1.0
    return min(1.0, max(0.0, resume_years) / min_years)


def _education_score(required: str | None, resume: str | None) -> float:
    """1.0 if the resume meets/exceeds the required level, 0.5 if present but
    lower, 0.0 if absent. Unknown levels fall back to a presence check."""
    req_rank = _education_rank(required)
    res_rank = _education_rank(resume)
    if req_rank is None:
        # Required level unrecognized: credit having *some* stated education.
        return 1.0 if resume else 0.0
    if res_rank is None:
        return 0.0
    if res_rank >= req_rank:
        return 1.0
    return 0.5


def score(
    *,
    requirements: JDRequirements,
    required_judgments: list[SkillJudgment],
    nice_judgments: list[SkillJudgment],
    resume_fields: ResumeFields,
    weights: ScoreWeights,
) -> ScoreResult:
    """Aggregate per-skill judgments + resume fields into a Match Score.

    A criterion only counts when it applies to this JD (e.g. experience is N/A
    when the JD states no minimum). The Match Score is the weighted average over
    the applicable criteria, so a JD that omits a criterion isn't penalized for
    it. Score and every criterion are in [0, 1].
    """
    raw: list[tuple[str, str, bool, float | None, float]] = [
        (
            "required_skills",
            "پوشش مهارت‌های الزامی",
            bool(requirements.required_skills),
            _coverage(required_judgments) if requirements.required_skills else None,
            weights.required_skills,
        ),
        (
            "nice_to_have_skills",
            "پوشش مهارت‌های امتیازی",
            bool(requirements.nice_to_have_skills),
            _coverage(nice_judgments) if requirements.nice_to_have_skills else None,
            weights.nice_to_have_skills,
        ),
        (
            "experience",
            "تطبیق سابقهٔ کاری",
            requirements.min_years_experience > 0,
            _experience_score(
                requirements.min_years_experience,
                resume_fields.total_years_experience,
            )
            if requirements.min_years_experience > 0
            else None,
            weights.experience,
        ),
        (
            "education",
            "تطبیق تحصیلات",
            requirements.education is not None,
            _education_score(requirements.education, resume_fields.education)
            if requirements.education is not None
            else None,
            weights.education,
        ),
    ]

    applicable_weight = sum(w for _, _, ok, _, w in raw if ok)

    components: list[ComponentScore] = []
    match_score = 0.0
    for key, label, ok, s, w in raw:
        contribution = 0.0
        if ok and s is not None and applicable_weight > 0:
            contribution = (w / applicable_weight) * s
            match_score += contribution
        components.append(
            ComponentScore(
                key=key,
                label=label,
                applicable=ok,
                score=s,
                weight=w,
                contribution=contribution,
            )
        )

    return ScoreResult(match_score=match_score, components=components)
