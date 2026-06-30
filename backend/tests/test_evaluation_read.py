"""EvaluationRead.from_evaluation — the single Evaluation→API deserializer.

The stored breakdown is read back through ScoreResult, so the breakdown shape
has one owner and drift surfaces as a validation error, not a silent KeyError.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas import EvaluationRead
from app.scoring.scorer import ComponentScore, ScoreResult
from app.scoring.weights import DEFAULT_WEIGHTS


def _stored_evaluation(breakdown: dict):
    """A duck-typed stand-in for the Evaluation ORM row (only the read columns)."""
    return SimpleNamespace(
        match_score=breakdown.get("match_score", 0.0),
        breakdown=breakdown,
        judgments=[{"skill": "Python", "verdict": "yes", "reason": None, "kind": "required"}],
        weights=DEFAULT_WEIGHTS.model_dump(),
    )


def test_round_trips_a_stored_breakdown():
    result = ScoreResult(
        match_score=0.8,
        components=[
            ComponentScore(
                key="required_skills",
                label="پوشش مهارت‌های الزامی",
                applicable=True,
                score=0.8,
                weight=0.5,
                contribution=0.8,
            )
        ],
    )
    read = EvaluationRead.from_evaluation(_stored_evaluation(result.model_dump()))

    assert read.match_score == 0.8
    assert [c.key for c in read.components] == ["required_skills"]
    assert read.judgments[0].skill == "Python"


def test_breakdown_drift_raises_validation_error_not_keyerror():
    # A breakdown missing "components" used to be a silent KeyError on raw access.
    with pytest.raises(ValidationError):
        EvaluationRead.from_evaluation(_stored_evaluation({"match_score": 0.5}))
