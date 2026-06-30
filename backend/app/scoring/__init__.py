"""Scoring: the deterministic scorer (pure) and the evaluation pipeline.

`score()` is the pure function (PRD "Seam 2"); `evaluate`/`upsert_evaluation`
wrap it with per-skill LLM judgments and persistence (Issue #5).
"""

from app.scoring.scorer import ComponentScore, ScoreResult, score
from app.scoring.service import (
    EvaluationOutcome,
    evaluate,
    rescore_job,
    upsert_evaluation,
)
from app.scoring.weights import DEFAULT_WEIGHTS, ScoreWeights

__all__ = [
    "ComponentScore",
    "ScoreResult",
    "score",
    "EvaluationOutcome",
    "evaluate",
    "upsert_evaluation",
    "rescore_job",
    "DEFAULT_WEIGHTS",
    "ScoreWeights",
]
