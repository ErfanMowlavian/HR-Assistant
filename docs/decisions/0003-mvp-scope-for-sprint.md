# ADR 0003 — MVP scope for a short solo sprint

- Status: Accepted
- Date: 2026-06-30

## Context
Real constraint: solo, ~1-2 day build, must be a working app with a live demo.
The original two-sided coaching product is a multi-month scope. We cut to a
defensible MVP we can finish and explain.

## Decision

### In scope (the project)
- **HR flow**: create/paste a Job Description, upload or paste candidate
  resumes, get a **ranked list** with a **score breakdown** per candidate.
- **LLM-extracts / math-ranks** pipeline from ADR-0002.
- **Resume input**: paste text OR upload PDF (simple text extraction via
  `pypdf`; no layout parsing).
- **Tiny gold-set evaluation**: 1 JD, ~8 resumes, report Precision@3 — the
  "how do we know it works" evidence.
- **Applicant flow (thin, Option B)**: applicant pastes resume + JD, gets a
  **read-only "what's missing" list** (JD skills not found in the resume).
  Does **not** feed back into ranking. First to be cut if time runs short.

### Out of scope (deliberately cut)
- Accounts / authentication (single app, HR view + applicant view).
- Applicant <-> AI back-and-forth chat or resume rewriting.
- PDF layout parsing, multi-file batch pipelines, async job queues.

### Stack
- Backend: **Python + FastAPI**, **SQLite**.
- Frontend: **Next.js + shadcn/ui**, minimal design.
- LLM: OpenAI-compatible provider via the existing `.env` settings.

### Deployment
- Local run is sufficient for the demo. Deploy (Vercel + a Python host) only
  if time remains after the core works.

## Consequences
- Honest, real git history. No fabricated timeline.
- The applicant flow is isolated so cutting it is a clean removal.
- Skill synonym matching (e.g. "JS" == "JavaScript") is an open question that
  affects both ranking and the "what's missing" list.
