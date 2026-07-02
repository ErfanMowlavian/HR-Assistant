# PRD — Persian HR Resume Ranking (MVP)

## Problem Statement

An HR person hiring for a role receives many resumes and has to read each one
and guess who fits the job best. It is slow, inconsistent, and hard to justify —
especially across resumes written in different styles, and in Persian where the
same skill may be written in Persian or English ("React" vs "ری‌اکت"). The HR
user cannot quickly answer "who are my best-matched candidates for this job, and
why?"

## Solution

A Persian, right-to-left web app where:

- **HR** writes a **Job Description (JD)**; the system extracts its structured
  requirements.
- **Applicants** browse open JDs, pick one, and paste (or upload) their resume
  as a **Submission**.
- The system produces an **Evaluation** per Submission — a **Match Score** with
  an explainable **Score Breakdown** and **per-skill judgments**.
- **HR** opens a JD and sees its Submissions **ranked** best-match first, each
  with the reasons behind the score.

The system is trustworthy by design: the **LLM reads** (extracts fields, judges
each required skill yes/partial/no), and **deterministic math ranks**. Ranking
quality is demonstrated with a small **Gold Set** and reported as **Precision@3
/ nDCG**.

## User Stories

1. As HR, I want to create a job description in Persian, so that I can start
   collecting and ranking candidates for a real role.
2. As HR, I want the system to extract the required skills, nice-to-have skills,
   minimum years of experience, education, and seniority from my JD text, so
   that I don't have to fill structured fields by hand.
3. As HR, I want to review and correct the extracted JD requirements, so that a
   bad extraction doesn't silently corrupt the ranking.
4. As HR, I want to see a list of all my job descriptions, so that I can manage
   multiple open roles.
5. As an applicant, I want to browse the open job descriptions, so that I can
   choose one to apply to.
6. As an applicant, I want to paste my resume text in Persian, so that I can
   apply without fighting a file uploader.
7. As an applicant, I want to optionally upload a PDF resume, so that I can
   reuse an existing document.
8. As an applicant, I want to be warned when my uploaded PDF extracts as garbled
   text, so that I can fall back to pasting and avoid a bad evaluation.
9. As an applicant, I want to submit my resume against a chosen JD, so that HR
   can consider me for that role.
10. As an applicant, I want to see a read-only "what's missing" gap report
    (skills the JD wants that my resume doesn't show), so that I understand my
    fit — without it changing my ranking.
11. As HR, I want each submission scored automatically against the JD, so that I
    don't read every resume blind.
12. As HR, I want submissions ranked best-match first for a JD, so that I can
    focus on the strongest candidates.
13. As HR, I want to see a score breakdown per candidate (required-skill
    coverage, nice-to-have coverage, experience match, education/seniority), so
    that I can justify the ranking.
14. As HR, I want to see the per-skill yes/partial/no judgments for a candidate,
    so that I can see exactly which requirements they meet.
15. As HR, I want skills written in Persian or English to be matched correctly,
    so that "React" and "ری‌اکت" are not treated as different skills.
16. As HR, I want Persian digits in resumes (e.g. years of experience) handled
    correctly, so that "۵ سال" is understood as 5 years.
17. As HR, I want to adjust the scoring weights, so that I can prioritise (e.g.)
    required skills over education for a given role.
18. As HR, I want sensible default weights, so that the system works well
    without configuration.
19. As HR, I want the dashboard to load instantly from stored results, so that a
    live demo never hangs on a slow or failing model call.
20. As HR, I want a "rank now" action to (re)run scoring on demand, so that I can
    prove the pipeline runs live.
21. As a user, I want the whole interface in Persian and right-to-left, so that
    it reads naturally.
22. As a developer, I want the app pre-seeded with one realistic Persian JD and
    ~8 resumes (with an obviously strongest candidate), so that the product can
    be demonstrated immediately.
23. As a developer, I want a gold set with known-good rankings, so that I can
    report Precision@3 / nDCG as evidence the ranking works.
24. As a developer, I want all model calls to go through one provider-agnostic
    gateway, so that I can swap providers via `.env` and test with a fake model.

## Implementation Decisions

- **Pipeline shape (ADR-0002, ADR-0004):** the LLM extracts structured fields
  and produces per-skill judgments (yes/partial/no); a deterministic scorer
  aggregates these into a weighted Match Score with a breakdown. The LLM never
  emits the final score.
- **Modules:**
  - *LLM gateway* — one interface (`extract_jd`, `extract_resume`,
    `judge_skill`) over **LiteLLM**, provider-agnostic via `.env`, with retries.
    The single injection seam for all model interaction.
  - *Extraction* — **Instructor + Pydantic v2** schema-constrained generation
    for JD requirements and resume fields; includes Persian-digit normalization.
  - *Scorer* — pure function: (JD requirements, per-skill judgments, extracted
    resume fields, weights) → Match Score + Score Breakdown. No I/O.
  - *Persistence* — SQLite with entities **Job Description**, **Submission**,
    **Evaluation** (and the read-only **Gap Report** derived from an Evaluation).
  - *API* — FastAPI endpoints for: create/list/get JD, submit/list Submissions
    for a JD, get ranked Evaluations for a JD, get a Gap Report, and a "rank
    now" action.
  - *Eval harness* — computes Precision@3 / nDCG over the Gold Set.
  - *Frontend* — Next.js + shadcn/ui, RTL, Vazirmatn font: HR dashboard (JD
    list, ranked candidates + breakdown), applicant submit view, gap report.
- **Scoring criteria & weights (ADR-0002):** required-skill coverage (highest),
  nice-to-have coverage, experience-years match, education/seniority match.
  Defaults ship; HR-adjustable.
- **Resume input (ADR-0004, ADR-0005):** paste-text primary; PDF best-effort via
  `pypdf` with a garbled-output heuristic that nudges the user to paste.
- **Demo mode (ADR-0005):** example data and its Evaluations are pre-computed
  and seeded into SQLite so the dashboard renders with no live model call; the
  same seeding logic is re-runnable live via "rank now".
- **No accounts (ADR-0003):** HR view and applicant view; identity is a typed
  display name only.
- **No LangChain (ADR-0005):** rejected as unnecessary abstraction.

## Testing Decisions

- **What makes a good test:** assert external behavior, not implementation
  details. Tests should not know how the scorer is wired internally, only that
  given inputs produce the right ranking/score and that API flows behave.
- **Seam 1 — LLM gateway (primary):** all model-dependent code depends on the
  gateway interface; tests inject a **fake LLM** returning canned
  extractions/judgments, so the whole app is testable with no real model call.
- **Seam 2 — deterministic scorer:** pure-function unit tests over crafted
  inputs (skill coverage, experience match, weight changes). The Gold Set eval
  (Precision@3 / nDCG) plugs in here.
- **Seam 3 — HTTP API:** FastAPI `TestClient` behavior tests for the real flows
  (create JD → submit → ranked list with breakdowns; gap report), with the LLM
  gateway stubbed via Seam 1.
- **Prior art:** none yet (greenfield); these three seams establish the testing
  conventions for the repo.

## Out of Scope

- Authentication / user accounts.
- Applicant ↔ AI back-and-forth chat or resume rewriting (the gap report is
  read-only and does not affect ranking).
- Robust PDF layout parsing; multi-file batch pipelines; async job queues.
- The gap report feeding back into ranking.
- Anything that depends on faking project history.

## Further Notes

- Persian-first, RTL throughout; mixed Persian/English skill text is expected
  and handled by per-skill LLM judgment, not string matching.
- Live deployment (Vercel + a Python host) is a stretch goal after the core
  works locally; a local run satisfies the demo requirement.
- Evidence-of-quality story for the demo/report: "LLM reads, deterministic math
  ranks, and Precision@3 on our gold set is the proof."
- See `docs/decisions/` (ADRs 0001–0005), `docs/glossary.md`, and
  `docs/domain-model.md` for the full design rationale.
