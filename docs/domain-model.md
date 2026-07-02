# Domain Model

The whole system is four entities and one flow. Terms match `glossary.md`.

## Entities

- **Job Description (JD)** — created by **HR**. Has a title, the full Persian
  text, and (after extraction) structured requirements: required skills,
  nice-to-have skills, minimum years, education, seniority.
- **Submission** — created by an **Applicant**. Belongs to exactly one JD.
  Holds the resume (pasted text, or text extracted from an uploaded PDF) and
  the applicant's display name.
- **Evaluation** — system-produced, one per Submission. Holds the **Match
  Score** (0–1), the **Score Breakdown**, and the **per-skill judgments**
  (yes/partial/no). This is what HR sees ranked.
- **Gap Report** (thin, Option B) — read-only, for the Applicant. Lists JD
  skills not demonstrated in their resume. Does **not** affect ranking.

## Flow

1. **HR** writes a JD (Persian text). System extracts its structured
   requirements (LLM, schema-constrained) and stores them.
2. **Applicant** browses open JDs, picks one, pastes resume (or uploads PDF),
   submits → a **Submission** tied to that JD.
3. System runs the pipeline on the Submission: extract resume fields → per-skill
   judgments against the JD → deterministic weighted **Match Score** + breakdown
   → stored as an **Evaluation**.
4. (Option B) Applicant may view a read-only **Gap Report** for their resume vs.
   the JD.
5. **HR** opens a JD and sees all its Submissions **ranked** by Match Score,
   each with its Score Breakdown (explainability).

## Notes
- No accounts. The app has an HR view and an Applicant view; identity is just a
  typed display name (ADR-0003).
- HR can adjust scoring weights (ADR-0002); defaults ship.
- Example data (one JD + ~8 Persian resumes) is seeded with pre-computed
  Evaluations for Demo Mode (ADR-0005).
