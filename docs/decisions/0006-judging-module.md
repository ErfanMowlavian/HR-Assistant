# ADR 0006 — A single module for per-skill judging

- Status: Accepted
- Date: 2026-06-30

## Context
Per-skill judging — "ask the gateway to judge each JD skill against a resume,
yes/partial/no, and never crash on a provider error" (ADR-0002) — had grown two
homes:

- `scoring/service.py` — `_judge()` (a try/except wrapper around
  `gateway.judge_skill`) plus the two list comprehensions in `evaluate()`.
- `gap.py` — `_verdict()` (a *second*, near-identical try/except wrapper,
  returning a bare `SkillVerdict` instead of a `SkillJudgment`) plus the loop in
  `build_gap_report()`.

The same responsibility was smeared across two modules: two graceful-failure
wrappers, two ways to iterate the required/nice skill lists, two return shapes.
The graceful-degradation behaviour (the part most likely to harbour a bug) was
reachable only through HTTP-level integration tests in each consumer.

## Decision
Introduce one module, `app/judging.py`, that owns per-skill judging:

- `judge_requirements(gateway, requirements, resume_text) -> JudgedRequirements`
  judges every required and nice-to-have skill, degrading any skill the gateway
  can't judge to a `no` verdict (carrying the error on `reason`).
- `JudgedRequirements` keeps the **required / nice split** the deterministic
  scorer needs, and exposes `tagged()` — the single place callers walk both
  groups (used by the flat persistence projection and the gap-report buckets).

Both consumers become thin:

- `scoring/service.evaluate` feeds `.required` / `.nice` into `score()`.
- `gap.build_gap_report` walks `tagged()` and buckets by verdict.

`app/judging.py` depends only on the gateway seam (`llm.gateway`) and the shared
types (`llm.types`) — **not** on the scorer. So the Gap Report stays cleanly
removable (ADR-0003, Option B): deleting `gap.py` touches neither `judging` nor
`scoring`.

## Consequences
- The graceful-failure policy has one home and one direct unit test
  (`tests/test_judging.py`) instead of being verified only through each
  consumer's HTTP tests.
- `_judge` and `_verdict` are deleted; their logic is concentrated, not moved
  (it passes the deletion test).
- Adding behaviour to judging (e.g. caching, batching, confidence) is a change
  in one module with two call sites, not a coordinated edit across scoring and
  the Gap Report.
- This is an internal deepening only: no API, scoring math, or ADR-0002 /
  ADR-0005 decision changes. All pre-existing tests pass unchanged.
