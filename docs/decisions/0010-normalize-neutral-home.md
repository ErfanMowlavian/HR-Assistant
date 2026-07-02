# ADR 0010 — A neutral home for digit normalization

- Status: Accepted
- Date: 2026-06-30

## Context
`normalize_digits` (Persian/Arabic → Latin digit folding, ADR-0004) lived in
`app/extraction/normalize.py`. But it is used in two stages:

- `extraction/service` folds the text **before the model reads it**, so numeric
  fields extract correctly.
- `scoring/scorer._education_rank` folds an **already-extracted value** before
  matching it against the education ranks.

Because it lived under `extraction/`, the pure Seam-2 scorer imported
`from app.extraction.normalize import normalize_digits` — the deterministic
scorer reaching into the extraction package for a generic text utility.

The architecture-review candidate framed this as "normalize once at intake."
That framing was **rejected**: the raw resume text is stored verbatim by design,
and the two folds operate on different data at different stages (model input vs.
extracted output) — they are not duplication to merge. The real friction was the
misplaced utility and the resulting cross-package import.

## Decision
Move `normalize_digits` to a neutral top-level module, `app/normalize.py`. Both
`extraction` and `scoring` import it from there; neither imports the other's
package. `extraction/__init__` no longer re-exports it (it was never an
extraction concept).

## Consequences
- The pure scorer no longer depends on the `extraction` package; the dependency
  graph reflects that digit folding is a shared text utility.
- Both call sites stay — they are different stages, not duplication.
- `tests/test_normalize.py` imports the new path; all pre-existing tests pass.
- No behaviour, API, or scoring-math change.
