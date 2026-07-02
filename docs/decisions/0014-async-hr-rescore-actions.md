# ADR 0014 — Extend async scoring to the HR re-score actions

- Status: Accepted
- Date: 2026-06-30

## Context
ADR-0013 made applicant submission async to escape the Next.js proxy's ~30s
timeout, but explicitly deferred the two HR-side actions that re-score *every*
submission of a JD:

- `PATCH /api/jobs/{id}/requirements` — editing requirements re-scores all
  candidates against the new criteria.
- `POST /api/jobs/{id}/rank` — the "rank now" button re-runs the pipeline live.

Both ran synchronously: N candidates × (skills) model calls, measured at
130–150s on a real model for ~7 candidates. Through the browser proxy that is a
guaranteed timeout → 500 — the same failure submission used to have, just on the
HR dashboard instead of the apply page.

## Decision
Apply the ADR-0013 pattern to both endpoints. Each now marks the JD's
submissions `status="processing"`, commits, schedules a background re-score, and
returns immediately — `PATCH` returns the updated JD, `POST /rank` returns the
current (now "processing") ranking. The dashboard's ranking panel polls until
every row settles.

- One shared worker, `submissions.rescore_job_in_background(session_factory,
  gateway, job_id)`: re-judges + re-scores every submission against current
  requirements and flips each to `done`/`failed`, committing per submission so
  the ranking fills in progressively. It does *not* re-extract — the resume text
  is unchanged, only the requirements moved — so it is cheaper than initial
  submission scoring. It lives beside `score_submission` (the background-scoring
  worker home) and is imported by both the jobs and ranking routers.
- `RankedCandidate` gained a `status` field so the dashboard can render a
  "در حال محاسبه…" spinner per row and know when to stop polling.
- Each per-submission LLM call still runs outside the write transaction; only
  the quick per-submission commit takes the lock (ADR-0012).

## Consequences
- The HR dashboard's "save requirements" and "rank now" return in milliseconds
  regardless of candidate count; no proxy timeout.
- API contract: `POST /rank` no longer returns freshly-scored rows in its
  response body — it returns the ranking as it stands (rows "processing"), and
  clients read the refreshed scores by polling `GET /ranking`. The two rank-now
  tests were updated to poll accordingly.
- The synchronous `scoring.rescore_job` orchestrator (ADR-0009) is now unused by
  the routers; it remains as the in-transaction primitive and is kept for its
  unit tests and as a building block. (Left in place deliberately; removing it is
  out of scope.)
- Coverage: `tests/test_async_scoring.py` gains rank-now and edit-requirements
  "processing → settles" cases. Suite at 107 passing.
- Verified live through the proxy: `PATCH` 0.06s, `POST /rank` 0.01s (was
  ~150s → 500); all 7 candidates re-scored to `done` in the background with
  correct scores; no proxy/backend errors.
