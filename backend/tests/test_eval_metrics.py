"""Unit tests for the pure ranking-quality metrics (Issue #6)."""

from __future__ import annotations

import math

from app.eval.metrics import dcg, ndcg, precision_at_k


def test_precision_at_k_counts_relevant_in_top_k():
    # Top 3 = [3, 1, 2]; relevant (>=2) are 3 and 2 → 2/3.
    assert precision_at_k([3, 1, 2, 0, 0], k=3) == 2 / 3


def test_precision_at_3_perfect_when_top3_all_strong():
    assert precision_at_k([3, 2, 2, 0, 1], k=3) == 1.0


def test_precision_at_k_threshold_is_respected():
    # With threshold 3, only the grade-3 item counts → 1/3.
    assert precision_at_k([3, 2, 2], k=3, threshold=3) == 1 / 3


def test_precision_at_k_empty_is_zero():
    assert precision_at_k([], k=3) == 0.0


def test_ndcg_is_one_for_ideal_ordering():
    assert ndcg([3, 3, 2, 2, 1, 0]) == 1.0


def test_ndcg_below_one_when_misordered():
    # A relevant candidate buried below an irrelevant one loses nDCG.
    assert ndcg([0, 3, 2, 1]) < 1.0


def test_ndcg_all_zero_is_zero():
    assert ndcg([0, 0, 0]) == 0.0


def test_dcg_matches_definition():
    rels = [3, 2, 0]
    expected = (2**3 - 1) / math.log2(2) + (2**2 - 1) / math.log2(3) + 0
    assert abs(dcg(rels) - expected) < 1e-9


def test_swapping_two_ranks_lowers_ndcg_below_ideal():
    ideal = ndcg([3, 2, 1, 0])
    swapped = ndcg([2, 3, 1, 0])
    assert ideal == 1.0
    assert swapped < ideal
