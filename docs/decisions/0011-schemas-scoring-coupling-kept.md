# ADR 0011 — HTTP schemas may reference scoring types (won't-change)

- Status: Accepted
- Date: 2026-06-30

## Context
An architecture review flagged that `app/schemas.py` (the HTTP response models)
imports `ComponentScore` from `scoring.scorer` and `ScoreWeights` from
`scoring.weights`, and exposes them directly in `EvaluationRead`. The concern:
the wire format tracks scoring internals, so a scorer refactor changes the API
contract.

This is recorded so the same suggestion is not re-raised by future reviews.

## Decision
Keep the coupling. `schemas.py` continues to reuse the scoring types directly.

## Rationale
- `ComponentScore` and `ScoreWeights` **are** the explainability contract
  (ADR-0002: every ranking exposes a per-criterion breakdown and the weights).
  They are not incidental internals that happen to leak; they are the values HR
  is meant to see. The API surfacing them is the intended design.
- Introducing parallel HTTP DTOs that mirror these models field-for-field would
  add a shallow mapping layer — interface as wide as the implementation — and a
  second place to edit on every breakdown change. That trades real **locality**
  for ceremony.
- For a solo MVP the direct reuse keeps one source of truth for the breakdown
  shape (reinforced by ADR-0007, where `ScoreResult` owns the stored shape).

## When to revisit
If the HTTP contract must evolve independently of the scorer — e.g. a public,
versioned API with external consumers, or a need to expose a breakdown shape
that deliberately differs from the internal one. None of those hold today.

## Consequences
- No code change.
- Future architecture reviews should treat this coupling as intentional and not
  re-suggest splitting it without one of the "revisit" conditions holding.
