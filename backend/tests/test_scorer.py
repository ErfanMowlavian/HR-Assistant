"""Seam 2 — the deterministic scorer as a pure function.

These tests know nothing about how scoring is wired into the app; they feed
crafted JD requirements, judgments, and resume fields straight into `score()`
and assert the Match Score and breakdown. Covers skill coverage, experience,
education, and the effect of changing weights (Issue #5 acceptance criteria).
"""

from __future__ import annotations

from app.llm.types import JDRequirements, ResumeFields, SkillJudgment, SkillVerdict
from app.scoring.scorer import score
from app.scoring.weights import DEFAULT_WEIGHTS, ScoreWeights


def _judgments(**verdicts: SkillVerdict) -> list[SkillJudgment]:
    return [SkillJudgment(skill=s, verdict=v) for s, v in verdicts.items()]


def _component(result, key: str):
    return next(c for c in result.components if c.key == key)


def test_full_required_coverage_scores_higher_than_none():
    reqs = JDRequirements(required_skills=["Python", "FastAPI"])
    resume = ResumeFields()

    full = score(
        requirements=reqs,
        required_judgments=_judgments(Python=SkillVerdict.YES, FastAPI=SkillVerdict.YES),
        nice_judgments=[],
        resume_fields=resume,
        weights=DEFAULT_WEIGHTS,
    )
    none = score(
        requirements=reqs,
        required_judgments=_judgments(Python=SkillVerdict.NO, FastAPI=SkillVerdict.NO),
        nice_judgments=[],
        resume_fields=resume,
        weights=DEFAULT_WEIGHTS,
    )

    assert full.match_score > none.match_score
    assert full.match_score == 1.0  # only required applies, fully covered
    assert none.match_score == 0.0


def test_partial_verdict_is_half_credit():
    reqs = JDRequirements(required_skills=["Python", "FastAPI"])
    result = score(
        requirements=reqs,
        required_judgments=_judgments(Python=SkillVerdict.YES, FastAPI=SkillVerdict.PARTIAL),
        nice_judgments=[],
        resume_fields=ResumeFields(),
        weights=DEFAULT_WEIGHTS,
    )
    # (1.0 + 0.5) / 2 = 0.75 over the only applicable criterion.
    assert _component(result, "required_skills").score == 0.75
    assert result.match_score == 0.75


def test_experience_match_scales_and_caps():
    reqs = JDRequirements(min_years_experience=4)
    low = score(
        requirements=reqs,
        required_judgments=[],
        nice_judgments=[],
        resume_fields=ResumeFields(total_years_experience=2.0),
        weights=DEFAULT_WEIGHTS,
    )
    over = score(
        requirements=reqs,
        required_judgments=[],
        nice_judgments=[],
        resume_fields=ResumeFields(total_years_experience=10.0),
        weights=DEFAULT_WEIGHTS,
    )
    assert _component(low, "experience").score == 0.5  # 2/4
    assert _component(over, "experience").score == 1.0  # capped, not 2.5
    assert over.match_score > low.match_score


def test_education_below_required_is_half_credit():
    reqs = JDRequirements(education="کارشناسی ارشد")
    meets = score(
        requirements=reqs,
        required_judgments=[],
        nice_judgments=[],
        resume_fields=ResumeFields(education="دکتری"),
        weights=DEFAULT_WEIGHTS,
    )
    below = score(
        requirements=reqs,
        required_judgments=[],
        nice_judgments=[],
        resume_fields=ResumeFields(education="کارشناسی"),
        weights=DEFAULT_WEIGHTS,
    )
    absent = score(
        requirements=reqs,
        required_judgments=[],
        nice_judgments=[],
        resume_fields=ResumeFields(education=None),
        weights=DEFAULT_WEIGHTS,
    )
    assert _component(meets, "education").score == 1.0
    assert _component(below, "education").score == 0.5
    assert _component(absent, "education").score == 0.0


def test_inapplicable_criteria_are_excluded_not_penalized():
    # JD asks only for required skills, fully met → perfect score even though
    # the JD names no nice-to-haves, no min years, and no education.
    reqs = JDRequirements(required_skills=["Python"])
    result = score(
        requirements=reqs,
        required_judgments=_judgments(Python=SkillVerdict.YES),
        nice_judgments=[],
        resume_fields=ResumeFields(),
        weights=DEFAULT_WEIGHTS,
    )
    assert result.match_score == 1.0
    assert _component(result, "experience").applicable is False
    assert _component(result, "experience").score is None


def test_weights_change_the_ranking():
    # A candidate strong on nice-to-haves but weak on experience vs. the reverse.
    reqs = JDRequirements(
        required_skills=["Python"],
        nice_to_have_skills=["Docker"],
        min_years_experience=10,
    )
    kwargs = dict(
        requirements=reqs,
        required_judgments=_judgments(Python=SkillVerdict.YES),
        nice_judgments=_judgments(Docker=SkillVerdict.YES),
        resume_fields=ResumeFields(total_years_experience=1.0),  # weak experience
    )

    experience_heavy = ScoreWeights(
        required_skills=0.1, nice_to_have_skills=0.1, experience=10.0, education=0.0
    )
    nice_heavy = ScoreWeights(
        required_skills=0.1, nice_to_have_skills=10.0, experience=0.1, education=0.0
    )

    # Same inputs, only the weights differ → different scores.
    low = score(weights=experience_heavy, **kwargs)
    high = score(weights=nice_heavy, **kwargs)
    assert high.match_score > low.match_score


def test_contributions_sum_to_match_score():
    reqs = JDRequirements(
        required_skills=["Python"],
        nice_to_have_skills=["Docker"],
        min_years_experience=3,
        education="کارشناسی",
    )
    result = score(
        requirements=reqs,
        required_judgments=_judgments(Python=SkillVerdict.YES),
        nice_judgments=_judgments(Docker=SkillVerdict.PARTIAL),
        resume_fields=ResumeFields(total_years_experience=3.0, education="کارشناسی"),
        weights=DEFAULT_WEIGHTS,
    )
    total = sum(c.contribution for c in result.components)
    assert abs(total - result.match_score) < 1e-9
    assert 0.0 <= result.match_score <= 1.0
