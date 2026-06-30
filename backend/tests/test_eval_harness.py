"""The eval harness over the committed Gold Set (Issue #6).

Run against the fake gateway, the numbers are deterministic and reproducible —
this is the CI-safe baseline. The same harness runs against the real provider
(`python -m app.eval --real`) for the headline number.
"""

from __future__ import annotations

from app.eval.harness import load_gold_set, run_eval
from app.llm.fake import FakeLLMGateway


def test_gold_set_is_well_formed():
    gold = load_gold_set()
    assert gold.requirements.required_skills  # JD has real requirements
    assert len(gold.resumes) >= 8  # ADR-0002: ~8–15 resumes
    # Ground truth spans the full relevance scale, with a clear strong tier.
    relevances = {r.relevance for r in gold.resumes}
    assert {0, 1, 2, 3} <= relevances


def test_fake_gateway_eval_is_reproducible_and_good():
    report = run_eval(FakeLLMGateway(), load_gold_set())
    # Deterministic baseline: the engineered Gold Set ranks ideally under the
    # substring fake. These exact numbers are documented in the README.
    assert report.precision_at_3 == 1.0
    assert report.ndcg == 1.0


def test_ranking_is_sorted_by_match_score_descending():
    report = run_eval(FakeLLMGateway(), load_gold_set())
    scores = [e.match_score for e in report.ranking]
    assert scores == sorted(scores, reverse=True)


def test_top_candidate_is_the_defensible_best():
    report = run_eval(FakeLLMGateway(), load_gold_set())
    top = report.ranking[0]
    assert top.applicant_name == "سارا محمدی"  # all skills, most experience, دکتری
    assert top.relevance == 3
