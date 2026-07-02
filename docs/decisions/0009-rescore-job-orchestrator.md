# ADR 0009 — One orchestrator for re-scoring a JD's submissions

- Status: Accepted
- Date: 2026-06-30

## Context
Two routers each inlined the same loop:

```python
for submission in job.submissions:
    upsert_evaluation(db, submission, job, gateway)
```

— `api/jobs.update_requirements` (requirements changed) and
`api/ranking.rank_now` (live re-score). The "fan over a JD's submissions and
re-score each" policy had no single home: a new parameter (e.g. `weights`) meant
finding and editing both loops. And `upsert_evaluation` — the validate → judge →
score → persist orchestrator — had no direct unit test; it was reachable only
through HTTP round-trips.

## Decision
Add one orchestrator, `scoring.rescore_job(db, job, gateway, *, weights)`, that
fans over `job.submissions` and upserts each Evaluation (skipping submissions
when the JD has no requirements). Both routers call it; neither spells the loop.

`submissions._create_submission` keeps its single `upsert_evaluation` call — it
scores only the one new submission, not the whole JD, so it is a different
operation and deliberately not routed through `rescore_job`.

`rescore_job` does not commit; the caller owns the transaction boundary (the
routers commit, matching their existing flow).

## Consequences
- One interface, two call sites: behaviour changes to the re-score policy
  happen in one signature.
- The orchestration is now unit-tested directly against an in-memory DB + fake
  gateway (`tests/test_scoring_service.py`): scores-and-persists, no-op without
  requirements, replace-in-place on re-run, and fan-over-all — instead of only
  through the ranking/jobs HTTP tests.
- No API response or scoring-math change; all pre-existing tests pass.
