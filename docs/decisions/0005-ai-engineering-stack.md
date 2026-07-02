# ADR 0005 — AI engineering stack

- Status: Accepted
- Date: 2026-06-30

## Context
The pipeline is: LLM extracts/judges structured fields from Persian JDs and
resumes; deterministic math ranks. We want a stack that is robust, explainable,
and a credible AI-engineering portfolio piece — without buzzwords the author
cannot defend.

## Decision
- **LiteLLM** as the provider-agnostic, OpenAI-compatible LLM gateway (matches
  the multi-provider `.env`), with retries and optional caching.
- **Pydantic v2** for typed schemas (JD requirements, extracted resume fields,
  per-skill judgments).
- **Instructor** for schema-constrained generation: LLM output is validated
  against the Pydantic schema with automatic retry on failure. No ad-hoc JSON
  parsing.
- **Evaluation harness**: a module computing Precision@k and nDCG over the
  Gold Set.
- **No LangChain.** Rejected as unnecessary abstraction the author would have
  to explain; the lighter stack is fully defensible and reads as more senior.

### Resume input
- **Paste text is primary.** **PDF upload is best-effort**: attempt extraction
  (`pypdf`), detect likely-garbled Persian output, and prompt the user to paste
  instead when extraction looks broken.

### Demo robustness
- **Demo mode**: example data + their rankings are pre-computed and stored in
  SQLite so the HR dashboard renders instantly without a live API call. A live
  "rank now" action remains to prove the pipeline runs.

## Consequences
- Provider can be swapped via `.env` with no code change.
- Schema-constrained extraction makes the pipeline robust to malformed output.
- A garbled-PDF heuristic is needed (e.g. low ratio of valid Persian/letters).
- Pre-computed rankings must be seeded by a script that is also re-runnable
  live.
