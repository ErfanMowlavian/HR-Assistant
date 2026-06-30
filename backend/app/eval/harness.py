"""Evaluation harness: run the real ranking pipeline over the Gold Set.

Loads the committed Gold Set (one Persian JD + human-labeled resumes), scores
each resume through the production scoring path (`scoring.evaluate` — the same
per-skill judgments + deterministic scorer the app uses), ranks by Match Score,
and reports Precision@3 and nDCG against the human relevance labels.

Run with the fake gateway for a deterministic, reproducible CI number; run with
the real gateway for the headline number on a live model.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from app.llm.gateway import LLMGateway
from app.llm.types import JDRequirements, ResumeFields
from app.scoring import DEFAULT_WEIGHTS, ScoreWeights, evaluate
from app.eval.metrics import ndcg, precision_at_k

GOLD_SET_PATH = Path(__file__).parent / "gold_set.json"


class GoldResume(BaseModel):
    applicant_name: str
    relevance: int  # human label, 0 (irrelevant) – 3 (strong)
    resume_text: str
    resume_fields: ResumeFields


class GoldSet(BaseModel):
    job_title: str
    job_text: str
    requirements: JDRequirements
    resumes: list[GoldResume]


class RankedEntry(BaseModel):
    applicant_name: str
    match_score: float
    relevance: int


class EvalReport(BaseModel):
    precision_at_3: float
    ndcg: float
    ranking: list[RankedEntry]


def load_gold_set(path: Path = GOLD_SET_PATH) -> GoldSet:
    return GoldSet.model_validate_json(path.read_text(encoding="utf-8"))


def run_eval(
    gateway: LLMGateway,
    gold: GoldSet | None = None,
    *,
    weights: ScoreWeights = DEFAULT_WEIGHTS,
) -> EvalReport:
    gold = gold or load_gold_set()

    scored = [
        RankedEntry(
            applicant_name=r.applicant_name,
            match_score=evaluate(
                gateway,
                requirements=gold.requirements,
                resume_fields=r.resume_fields,
                resume_text=r.resume_text,
                weights=weights,
            ).score.match_score,
            relevance=r.relevance,
        )
        for r in gold.resumes
    ]
    scored.sort(key=lambda e: e.match_score, reverse=True)

    ranked_relevances = [e.relevance for e in scored]
    return EvalReport(
        precision_at_3=precision_at_k(ranked_relevances, k=3, threshold=2),
        ndcg=ndcg(ranked_relevances),
        ranking=scored,
    )
