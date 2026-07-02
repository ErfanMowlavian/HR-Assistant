# ADR 0013 — Asynchronous submission scoring

- Status: Accepted
- Date: 2026-06-30

## Context
Applicants submitting through the browser got a 500. The browser calls `/api/…`
on the Next.js server, which proxies to the backend; that proxy aborts a request
after ~30s (`socket hang up` / ECONNRESET). But a real-model submission takes
~40s — one resume extraction plus N per-skill judgments, run sequentially — so
the proxy killed the connection before the backend finished and returned its own
`Internal Server Error`.

Direct backend calls succeeded (no proxy, no timeout), which is why the
end-to-end API test passed while the browser failed. The earlier "database is
locked" fix (ADR-0012) was real and necessary, but underneath it sat a second,
independent problem: a single synchronous request simply does too much slow work
to survive a reverse proxy — and would equally fail behind any CDN/load balancer
with a similar idle cap.

Options weighed: (a) parallelize the LLM calls — faster, but on a free tier the
concurrent calls risk rate-limit-induced score degradation, and a slow day could
still breach 30s; (b) bypass the proxy with direct browser→backend calls + CORS —
drops the same-origin design and needs a public backend URL; (c) make scoring
asynchronous. We chose (c): it removes the slow work from the request entirely,
so correctness never depends on how fast the model is.

## Decision
`POST /submissions` (and `/submissions/upload`) now persist the raw resume
immediately and return **201 with `status="processing"`**, then schedule a
FastAPI background task that does the extraction + judging + scoring and flips
the row to `"done"` (or `"failed"` on an unexpected error). The applicant gets an
instant response; the request never holds open across the model call.

- New `submissions.status` column: `processing` | `done` | `failed`. An additive
  migration (`db._add_submission_status_column`) backfills pre-existing rows to
  `done` (they were scored synchronously at submit time). Seeded rows are set
  `done` explicitly.
- The background worker (`score_submission`) opens its own session via a new
  `get_sessionmaker` dependency — the request's session is closed once the
  response is sent. Injecting the *factory* (not importing `SessionLocal`) keeps
  the worker pointed at whatever DB the request used, so tests run it against
  their isolated in-memory DB. It still does all LLM I/O before the write, so the
  short-write-lock invariant from ADR-0012 holds.
- New `GET /submissions/{id}` so the apply page can poll until `status` settles;
  the page shows a "در حال بررسی…" spinner, then the extracted skills (or a
  graceful note on `failed`).
- The combined sync helper (`evaluate_submission` + `store_outcome`, ADR-0012)
  is reused by the worker — the two compose cleanly.

## Consequences
- Browser submissions return in milliseconds; no proxy timeout can occur,
  regardless of model latency.
- The API contract changed: the create response no longer carries extracted
  fields — clients read them by polling the submission. Tests that asserted on
  the create body were updated to poll (TestClient runs background tasks
  synchronously, so a follow-up read is already `done`).
- A genuinely unexpected (non-gateway) worker error marks the row `failed` rather
  than leaving it stuck on `processing`, so the UI stops polling.
- Coverage: `tests/test_async_scoring.py` (create→processing then poll→done,
  failed-path safety net, 404 on missing submission). Suite at 105 passing.
- **Not addressed here:** the HR-side re-score actions — `PATCH …/requirements`
  and `POST …/rank` — re-score every submission synchronously and have the same
  proxy-timeout exposure for large JDs. They are HR-triggered and lower-frequency;
  moving them to the same background pattern is a natural follow-up.
