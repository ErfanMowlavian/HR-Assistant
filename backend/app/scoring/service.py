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

from app.judging import judge_requirements
from app.llm.gateway import LLMGateway
from app.llm.types import JDRequirements, ResumeFields
from app.models import Evaluation, JobDescription, Submission
from app.scoring.scorer import ScoreResult, score
from app.scoring.weights import DEFAULT_WEIGHTS, ScoreWeights


@dataclass
class EvaluationOutcome:
    """What an evaluation produces: the score breakdown and the judgments."""

    score: ScoreResult
    judgments: list[dict]  # {skill, verdict, reason, kind} — kind: required|nice


def evaluate(
    gateway: LLMGateway,
    *,
    requirements: JDRequirements,
    resume_fields: ResumeFields | None,
    resume_text: str,
    weights: ScoreWeights = DEFAULT_WEIGHTS,
) -> EvaluationOutcome:
    """Judge every JD skill against the resume, then score deterministically."""
    judged = judge_requirements(gateway, requirements, resume_text)

    result = score(
        requirements=requirements,
        required_judgments=judged.required,
        nice_judgments=judged.nice,
        resume_fields=resume_fields or ResumeFields(),
        weights=weights,
    )

    judgments = [
        {"skill": j.skill, "verdict": j.verdict.value, "reason": j.reason, "kind": kind}
        for kind, j in judged.tagged()
    ]
    return EvaluationOutcome(score=result, judgments=judgments)


def evaluate_submission(
    gateway: LLMGateway,
    submission: Submission,
    job: JobDescription,
    *,
    weights: ScoreWeights = DEFAULT_WEIGHTS,
) -> EvaluationOutcome | None:
    """The LLM half of scoring one Submission: judge + score, touching no DB.

    Returns None when the JD has no extracted requirements yet — nothing to
    score against. Pulling this out of `upsert_evaluation` lets the submission
    hot path run the (slow) judging *before* opening a write transaction, so the
    SQLite write lock is never held across network I/O.
    """
    if not job.requirements:
        return None

    requirements = JDRequirements.model_validate(job.requirements)
    resume_fields = (
        ResumeFields.model_validate(submission.resume_fields)
        if submission.resume_fields
        else None
    )
    return evaluate(
        gateway,
        requirements=requirements,
        resume_fields=resume_fields,
        resume_text=submission.resume_text,
        weights=weights,
    )


def store_outcome(
    db: Session,
    submission: Submission,
    outcome: EvaluationOutcome,
    *,
    weights: ScoreWeights = DEFAULT_WEIGHTS,
) -> Evaluation:
    """The DB half of scoring: persist a computed outcome as the one Evaluation
    per Submission (re-running replaces it in place). Fast and I/O-free, so it
    is safe to call inside a short write transaction."""
    evaluation = submission.evaluation or Evaluation(submission_id=submission.id)
    evaluation.match_score = outcome.score.match_score
    evaluation.breakdown = outcome.score.model_dump()
    evaluation.judgments = outcome.judgments
    evaluation.weights = weights.model_dump()
    evaluation.submission = submission
    db.add(evaluation)
    return evaluation


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

    Note: this judges (network I/O) *and* writes within the caller's
    transaction. The submission hot path instead splits the two
    (`evaluate_submission` then `store_outcome`) to keep the write lock short;
    this combined form remains the convenient one for HR-side rescoring.
    """
    outcome = evaluate_submission(gateway, submission, job, weights=weights)
    if outcome is None:
        return None
    return store_outcome(db, submission, outcome, weights=weights)


def rescore_job(
    db: Session,
    job: JobDescription,
    gateway: LLMGateway,
    *,
    weights: ScoreWeights = DEFAULT_WEIGHTS,
) -> list[Evaluation]:
    """Re-score every submission of a JD against its current requirements.

    The one home for "fan over a JD's submissions and upsert each Evaluation",
    used when HR edits the requirements and by the live "rank now" action.
    A no-op per submission when the JD has no requirements yet. Does not commit —
    the caller owns the transaction boundary.
    """
    evaluations = [
        upsert_evaluation(db, submission, job, gateway, weights=weights)
        for submission in job.submissions
    ]
    return [e for e in evaluations if e is not None]
