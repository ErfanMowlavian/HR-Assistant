"""Evaluation pipeline: per-skill judgments (LLM) → deterministic score (math).

This is where the two halves meet. `evaluate()` asks the gateway to judge each
required and nice-to-have skill against the raw resume text, then hands those
judgments to the pure `score()` function. `upsert_evaluation()` persists the
result as the one Evaluation per Submission (re-running replaces it in place),
so the dashboard can render instantly from stored results (story #19).

A judgment that the gateway can't produce (provider error) degrades to a "no"
verdict for that one skill rather than failing the whole evaluation — a flaky
model lowers a score, it never crashes the ranking.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.llm.gateway import LLMGateway
from app.llm.types import JDRequirements, ResumeFields, SkillJudgment, SkillVerdict
from app.models import Evaluation, JobDescription, Submission
from app.scoring.scorer import ScoreResult, score
from app.scoring.weights import DEFAULT_WEIGHTS, ScoreWeights


@dataclass
class EvaluationOutcome:
    """What an evaluation produces: the score breakdown and the judgments."""

    score: ScoreResult
    judgments: list[dict]  # {skill, verdict, reason, kind} — kind: required|nice


def _judge(gateway: LLMGateway, skill: str, resume_text: str) -> SkillJudgment:
    try:
        return gateway.judge_skill(skill, resume_text)
    except Exception as exc:  # provider error: treat as unmet, never crash
        return SkillJudgment(skill=skill, verdict=SkillVerdict.NO, reason=str(exc))


def evaluate(
    gateway: LLMGateway,
    *,
    requirements: JDRequirements,
    resume_fields: ResumeFields | None,
    resume_text: str,
    weights: ScoreWeights = DEFAULT_WEIGHTS,
) -> EvaluationOutcome:
    """Judge every JD skill against the resume, then score deterministically."""
    required = [_judge(gateway, s, resume_text) for s in requirements.required_skills]
    nice = [_judge(gateway, s, resume_text) for s in requirements.nice_to_have_skills]

    result = score(
        requirements=requirements,
        required_judgments=required,
        nice_judgments=nice,
        resume_fields=resume_fields or ResumeFields(),
        weights=weights,
    )

    judgments = [
        {"skill": j.skill, "verdict": j.verdict.value, "reason": j.reason, "kind": kind}
        for kind, group in (("required", required), ("nice", nice))
        for j in group
    ]
    return EvaluationOutcome(score=result, judgments=judgments)


def upsert_evaluation(
    db: Session,
    submission: Submission,
    job: JobDescription,
    gateway: LLMGateway,
    *,
    weights: ScoreWeights = DEFAULT_WEIGHTS,
) -> Evaluation | None:
    """Compute and store the Evaluation for one Submission.

    Returns None (and stores nothing) when the JD has no extracted requirements
    yet — there's nothing to score against, so the candidate simply shows as
    "not yet evaluated" until HR fills the requirements in.
    """
    if not job.requirements:
        return None

    requirements = JDRequirements.model_validate(job.requirements)
    resume_fields = (
        ResumeFields.model_validate(submission.resume_fields)
        if submission.resume_fields
        else None
    )

    outcome = evaluate(
        gateway,
        requirements=requirements,
        resume_fields=resume_fields,
        resume_text=submission.resume_text,
        weights=weights,
    )

    evaluation = submission.evaluation or Evaluation(submission_id=submission.id)
    evaluation.match_score = outcome.score.match_score
    evaluation.breakdown = outcome.score.model_dump()
    evaluation.judgments = outcome.judgments
    evaluation.weights = weights.model_dump()
    evaluation.submission = submission
    db.add(evaluation)
    return evaluation
