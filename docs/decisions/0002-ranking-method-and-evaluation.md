# ADR 0002 — Ranking method and how we evaluate it

- Status: Accepted
- Date: 2026-06-30

## Context
"Rank the best resumes" was undefined. An LLM will emit a confident ranked
list for any input, which is not evidence the ranking is correct. We need a
definition of "best match" that is explainable and an evaluation method that
produces a defensible number.

## Decision

### Scoring: LLM reads, math judges
- The **LLM extracts structured fields**, not scores:
  - From the JD: required skills, nice-to-have skills, minimum years of
    relevant experience, required education level, seniority.
  - From each resume: skills, total relevant years, titles, education.
- A **deterministic weighted score** ranks candidates over those fields:
  - required-skill coverage (highest weight)
  - nice-to-have skill coverage
  - experience-years match
  - education / seniority match
- Default weights ship with the system; **HR can adjust the weights**.
- Every ranking exposes a **score breakdown** per candidate (explainability).

### Evaluation: gold set + standard metric
- Build a small **gold set**: ~3 JDs, ~10-15 resumes each, with human labels
  for who the strong candidates are (or a human ranking).
- Report **Precision@3** and **nDCG** (or Spearman's rank correlation) of the
  system ranking vs. the gold ranking.

## Consequences
- The LLM is confined to extraction/normalization; ranking is consistent and
  auditable.
- Skill matching must handle synonyms/variants (e.g., "JS" == "JavaScript") —
  carried forward as an open question.
- Building the gold set is real work and must be scheduled, not skipped.
- "Best match" is now defined as the weighted-coverage score above.
