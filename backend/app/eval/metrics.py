"""Ranking-quality metrics — pure functions over graded relevance labels.

All three take the ground-truth relevance grades of candidates *in the order
the system ranked them* (index 0 = the system's top pick) and return a number.
No I/O; trivially unit-testable. These are the "how do we know it works?"
numbers (ADR-0002, glossary: Precision@3 / nDCG).
"""

from __future__ import annotations

import math


def precision_at_k(ranked_relevances: list[int], k: int = 3, threshold: int = 2) -> float:
    """Fraction of the top-k ranked candidates that are actually relevant.

    A candidate counts as relevant when its graded relevance is >= threshold
    (default: 2 on a 0–3 scale, i.e. "strong" or better).
    """
    top = ranked_relevances[:k]
    if not top:
        return 0.0
    return sum(1 for rel in top if rel >= threshold) / len(top)


def dcg(ranked_relevances: list[int]) -> float:
    """Discounted Cumulative Gain with the standard 2^rel - 1 gain."""
    return sum(
        (2**rel - 1) / math.log2(i + 2)
        for i, rel in enumerate(ranked_relevances)
    )


def ndcg(ranked_relevances: list[int]) -> float:
    """Normalized DCG in [0, 1]: the system's DCG over the ideal ordering's DCG.

    1.0 means the system ordered candidates exactly by relevance; lower means
    relevant candidates were ranked below less-relevant ones.
    """
    ideal = dcg(sorted(ranked_relevances, reverse=True))
    if ideal == 0:
        return 0.0
    return dcg(ranked_relevances) / ideal
