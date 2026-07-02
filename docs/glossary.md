# Glossary — Ubiquitous Language

Terms we agree to use consistently across code, UI, and docs. One word per
concept; no synonyms drifting in.

| Term | Meaning | Notes |
|------|---------|-------|
| **Job Description (JD)** | The role definition HR is hiring for. The thing resumes are ranked *against*. | Source of the ranking criteria. |
| **Resume** | A candidate's submitted document/profile. | Format(s) TBD. |
| **Applicant** | A person who submits a resume for a JD. | Client-side user. |
| **HR** | The hiring-side user who reviews rankings. | Admin-side user. The primary customer (ADR-0001). |
| **Ranking** | An ordered list of applicants for one JD, "best match" first. | The core output (ADR-0002). |
| **Match Score** | Deterministic weighted score of one resume vs one JD, over extracted structured fields. | Range 0–1. Explainable via breakdown. |
| **Score Breakdown** | The per-criterion sub-scores that sum to a Match Score. | Required for explainability. |
| **Structured Fields** | The typed data the LLM extracts from a JD or resume (skills, years, education, etc.). | LLM extracts; math ranks. |
| **Gold Set** | A small human-labeled set of JDs + resumes used as ground truth for evaluation. | ~3 JDs, ~10–15 resumes each. |
| **Precision@3 / nDCG** | Metrics comparing system ranking to the Gold Set ranking. | The "how do we know it works" numbers. |
| **Per-skill Judgment** | LLM verdict for one required skill against one resume: yes / partial / no. | Handles synonyms & mixed Persian/English script. Aggregated by the scorer. |
| **Judged Requirements** | The per-skill judgments for one resume against a JD, kept in their required / nice-to-have split. | Produced once by the judging module (`app/judging.py`); consumed by both the scorer and the Gap Report. Degrades a skill to *no* on provider error. |
| **Schema-constrained Generation** | LLM output forced to match a Pydantic schema, auto-retried on validation failure (via Instructor). | Robust parsing, no regex hacks. |
| **Demo Mode** | Pre-computed rankings seeded into SQLite so the dashboard renders with no live API call. | Insurance against a live-API failure during the demo. |
| **Submission** | One applicant's resume sent against one chosen JD. | The unit applicants create. |
| **Evaluation (entity)** | The stored result of scoring one Submission against its JD: Match Score + Score Breakdown + per-skill judgments. | What HR sees ranked. |
