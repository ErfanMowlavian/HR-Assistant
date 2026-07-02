# ADR 0012 — No network I/O inside a write transaction (SQLite write-lock fix)

- Status: Accepted
- Date: 2026-06-30

## Context
Concurrent applicants submitting resumes at the same time intermittently got a
500. The cause was `sqlite3.OperationalError: database is locked`.

A submission's hot path (`submissions._create_submission`) did:

```python
db.add(submission)
db.flush()                         # opens the write transaction, takes the lock
upsert_evaluation(db, submission, job, gateway)  # judges every skill — 10–20s of LLM I/O
db.commit()                        # releases the lock
```

SQLite permits only one writer. Because the per-skill judging (multi-second
network I/O) ran *inside* the open transaction, the write lock was held for the
whole duration. A second submission arriving in that window could not acquire
the lock, and with no `busy_timeout` configured it failed immediately rather
than waiting. One-at-a-time testing never hit it; real overlapping traffic did.

## Decision
Two changes, addressing the cause and adding a safety net:

1. **Do all LLM work before opening the transaction.** Split the combined
   `upsert_evaluation` into its two halves:
   - `scoring.evaluate_submission(gateway, submission, job)` — judge + score,
     touching no DB (returns `None` when the JD has no requirements yet).
   - `scoring.store_outcome(db, submission, outcome)` — persist a computed
     outcome, fast and I/O-free, safe inside a short transaction.

   `_create_submission` now extracts and judges first, then opens the write
   transaction only to `add` → `flush` → `store_outcome` → `commit`. The lock is
   held for milliseconds. `upsert_evaluation` remains as `evaluate_submission`
   then `store_outcome` for the HR-side `rescore_job` path, which is a single
   user and not subject to applicant concurrency.

2. **Make SQLite tolerant of concurrent writers** in `db.make_engine`, via a
   `connect` listener that runs `PRAGMA journal_mode=WAL` (readers never block a
   writer) and `PRAGMA busy_timeout=30000` (a writer waits up to 30s for the
   lock instead of erroring on the spot).

## Consequences
- Concurrent submissions no longer 500. The write lock is contended only for the
  brief persist step, and overlapping writers queue rather than fail.
- New invariant for the codebase: a gateway (network) call must not run inside an
  open write transaction. `evaluate_submission` / `store_outcome` make that easy
  to honour at the seam between "the LLM reads" and "the DB writes".
- Regression coverage (`tests/test_submission_concurrency.py`): a real on-disk
  SQLite DB + two threads whose judging is barrier-synchronised so the
  submissions provably overlap — both return 201. The old ordering deadlocks this
  test. A second test asserts the WAL + busy_timeout pragmas are applied.
- No API response or scoring-math change; all pre-existing tests pass (102 total).
- WAL adds `-wal`/`-shm` sidecar files next to the SQLite file; fine on the
  Docker named volume and local disk.
