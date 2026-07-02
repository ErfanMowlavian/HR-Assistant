# ADR 0007 — One owner for the stored breakdown shape

- Status: Accepted
- Date: 2026-06-30

## Context
An Evaluation stores its score breakdown as opaque JSON
(`Evaluation.breakdown`). The shape `{match_score, components}` is defined by
`ScoreResult` (scorer), written by `scoring.service` via `score.model_dump()`,
and read back in `api/ranking.evaluation_read` by **raw key**:
`evaluation.breakdown["components"]`.

Three places knew the shape, and the read side knew it by string key — so a
rename or restructure of `ScoreResult` would surface as a silent `KeyError` at
request time, invisible to the type checker and caught only by an HTTP test.

## Decision
Read the stored breakdown back **through the model that owns it**, in one
place: `EvaluationRead.from_evaluation(evaluation)` (a classmethod on the API
schema) does `ScoreResult.model_validate(evaluation.breakdown)` and projects the
components.

- `api/ranking` drops its `evaluation_read()` helper and calls
  `EvaluationRead.from_evaluation(...)`.
- `ScoreResult` becomes the single owner of the breakdown JSON shape; no caller
  spells `"components"`.

The schema's reference to the `Evaluation` ORM type is import-only under
`TYPE_CHECKING` (the body is duck-typed over the read columns), so no import
cycle and no runtime coupling to the ORM.

## Consequences
- Breakdown drift is caught as a Pydantic `ValidationError` at the read seam,
  not a silent `KeyError`.
- The Evaluation→API reconstruction has one home and a direct unit test
  (`tests/test_evaluation_read.py`) — round-trip plus the drift case — instead
  of being exercised only through the ranking HTTP tests.
- The breakdown's storage shape can evolve by changing `ScoreResult` alone.
- Internal deepening only: no API response shape change, no scoring-math change.
  All pre-existing tests pass unchanged.
