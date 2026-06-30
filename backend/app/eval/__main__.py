"""CLI: run the Gold Set evaluation.

    python -m app.eval            # fake gateway — deterministic, reproducible
    python -m app.eval --real     # real provider via .env — the headline number

Prints Precision@3 and nDCG plus the system's ranking with each candidate's
human relevance label, so a mis-ranking is easy to spot.
"""

from __future__ import annotations

import argparse

from app.eval.harness import load_gold_set, run_eval
from app.llm.gateway import LLMGateway


def _build_gateway(real: bool) -> LLMGateway:
    if real:
        from app.llm.litellm_gateway import LiteLLMGateway

        return LiteLLMGateway()
    from app.llm.fake import FakeLLMGateway

    return FakeLLMGateway()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Gold Set ranking evaluation.")
    parser.add_argument(
        "--real",
        action="store_true",
        help="Use the real LLM provider (.env) instead of the deterministic fake.",
    )
    args = parser.parse_args()

    gold = load_gold_set()
    report = run_eval(_build_gateway(args.real), gold)

    gateway_label = "real provider" if args.real else "fake gateway (deterministic)"
    print(f"Gold Set: {gold.job_title} — {len(gold.resumes)} resumes [{gateway_label}]")
    print(f"  Precision@3: {report.precision_at_3:.3f}")
    print(f"  nDCG:        {report.ndcg:.3f}")
    print("\n  rank  score   rel  candidate")
    print("  ----  -----   ---  ---------")
    for i, e in enumerate(report.ranking, start=1):
        print(f"  {i:>4}  {e.match_score:.3f}    {e.relevance}   {e.applicant_name}")


if __name__ == "__main__":
    main()
