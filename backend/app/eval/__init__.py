"""Evaluation harness + ranking-quality metrics over the Gold Set (Issue #6).

`run_eval` runs the real scoring pipeline over the committed Gold Set and
reports Precision@3 / nDCG; `metrics` holds the pure metric functions.
"""

from app.eval.harness import EvalReport, GoldSet, load_gold_set, run_eval
from app.eval.metrics import dcg, ndcg, precision_at_k

__all__ = [
    "EvalReport",
    "GoldSet",
    "load_gold_set",
    "run_eval",
    "dcg",
    "ndcg",
    "precision_at_k",
]
