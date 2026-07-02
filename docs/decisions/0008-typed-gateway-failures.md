# ADR 0008 — Typed gateway failures at the seam

- Status: Accepted
- Date: 2026-06-30

## Context
`extraction/service.py` caught every failure of a gateway call and flattened it
into one `ExtractionError(str(exc))` — the comment literally read "provider
error, validation failure, timeout…". A caller could tell *that* extraction
failed but not *why*: was the model unreachable (transient — retry), or did it
respond with off-schema output (retrying won't help)?

That distinction is exactly what the Bynara provider incident surfaced: an
unreachable/forbidden provider is a different situation from a model that
answers but off-schema, and they warrant different responses.

## Decision
Give the gateway seam a typed failure vocabulary (`app/llm/errors.py`):

- `GatewayError` — base; catch it to degrade gracefully on any cause.
- `ProviderUnavailable` — transport / auth / timeout / rate limit. Transient.
- `InvalidModelOutput` — the model responded, but off-schema.

The **adapter that knows the provider does the classification.** `LiteLLMGateway`
wraps its call and maps raw litellm/Instructor exceptions via a pure
`_classify_gateway_error` (pydantic `ValidationError` or an Instructor
retry-exhaustion exception → `InvalidModelOutput`; everything else →
`ProviderUnavailable`). The extraction layer no longer guesses: it lets typed
`GatewayError`s through, maps its own boundary re-validation failure to
`InvalidModelOutput`, and treats any unclassified exception as
`ProviderUnavailable`.

`ExtractionError` is retired; the consumers (`api/jobs`, `api/submissions`)
catch the base `GatewayError`, so their graceful "persist with null fields"
behaviour is unchanged.

## Consequences
- The cause now rides the seam: a caller can branch on `ProviderUnavailable`
  vs `InvalidModelOutput` without importing litellm or instructor.
- The classifier is a pure function with a direct unit test
  (`tests/test_gateway_errors.py`); extraction's mapping is tested in
  `tests/test_extraction_service.py`.
- Surfacing the cause to the API/UI (e.g. "model unreachable — retry" vs
  "couldn't read this JD") is now a small, well-defined follow-up — deliberately
  out of scope here; current behaviour and the API response are unchanged.
- All pre-existing tests pass.
