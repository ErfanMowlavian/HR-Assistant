# HR Assistant — Persian Resume Ranking (MVP)

A Persian, right-to-left web app that ranks résumés against a Job Description.
The **LLM reads** (extracts structured fields, judges each skill yes/partial/no)
and **deterministic math ranks** — explainable by design. See the PRD
([issue #1](https://github.com/ErfanMowlavian/HR-Assistant/issues/1)) and the
ADRs/glossary/domain model under `docs/`.

Implemented so far:

- **Issue #2 — walking skeleton.** HR creates a Job Description (title + Persian
  text), it persists in SQLite, and shows up in a Persian RTL dashboard. Stands
  up every layer the later slices build on: FastAPI + SQLite, the injectable
  LLM-gateway seam with a fake implementation, and the Next.js + shadcn/ui RTL
  shell with the Vazirmatn font.
- **Issue #3 — JD requirement extraction + review.** Creating a JD triggers
  schema-constrained extraction of its structured requirements (required /
  nice-to-have skills, minimum years, education, seniority) through the gateway;
  Persian/Arabic digits are normalized before numeric reasoning. HR can review
  and correct the extracted requirements (`PATCH /api/jobs/{id}/requirements`),
  validated by the same Pydantic schema. If the model is unreachable or returns
  off-schema output, the JD is still saved with `requirements: null` and flagged
  so nothing is lost or silently corrupted.

- **Issue #4 — applicant submission + resume extraction.** An applicant browses
  open JDs, picks one, and pastes a resume (+ display name) to create a
  Submission tied to that JD (`POST /api/jobs/{id}/submissions`). Resume fields
  (skills, total years, titles, education) are extracted on submission, reusing
  the same normalize→gateway→validate infra; the raw resume text is stored
  verbatim so mixed Persian/English skill text is preserved for per-skill
  judgment (#5). Failed extraction is graceful (fields null + flagged), same as
  JD extraction.

- **Issue #5 — scoring & ranked HR dashboard (the core).** For each Submission
  the gateway judges every JD skill (required + nice-to-have) against the resume
  as **yes / partial / no**, and a **deterministic scorer** (a pure function —
  the second test seam) aggregates those judgments with experience and
  education into a weighted **Match Score** and per-criterion **breakdown**,
  stored as an **Evaluation** (one per Submission). Submissions are scored on
  arrival and re-scored when HR edits the JD's requirements, so HR opens a JD
  and sees its candidates **ranked best-match first** (`GET
  /api/jobs/{id}/ranking`) — each with its score breakdown and per-skill
  verdicts — rendered instantly from stored results. Persian/English skill
  synonyms ("React" == "ری‌اکت") are matched by the gateway's judgment, not by
  string equality. **Default weights ship** (required-skill coverage weighted
  highest) and are passed into the scorer, so they can be overridden later.

- **Issue #6 — gold set + evaluation harness.** The evidence-of-quality slice:
  a committed Persian **Gold Set** (one JD + 10 human-labeled resumes, graded
  0–3) and a harness that runs the **real ranking pipeline** over it and reports
  **Precision@3** and **nDCG** — the project's answer to "how do you know it
  works?". The same harness runs against the fake gateway (deterministic CI
  baseline) or the real provider (headline number). See
  [Evaluation](#evaluation-issue-6).

- **Issue #7 — demo mode: seed data + "rank now".** Demo robustness. A **seed
  command** (`python -m app.seed`) loads one realistic Persian JD + ~10 resumes
  from the Gold Set **with their Evaluations pre-computed and stored**, so HR
  opens the dashboard and the ranked list renders **instantly with no live model
  call** (the `GET /ranking` path has no gateway dependency at all). The seed
  uses the deterministic fake gateway, so it works with the model provider
  unreachable, and the seeded ranking has a clear, defensible top candidate
  (سارا محمدی, 1.000, monotonically down to irrelevant ones). A **"rank now"**
  action (`POST /api/jobs/{id}/rank`) re-runs the pipeline **live** for a JD —
  the on-demand proof that scoring works. See [Demo mode](#demo-mode-issue-7).

Tests run entirely against the fake gateway — no real model call.

## Architecture

```
backend/   FastAPI + SQLite, the LLM-gateway seam, tests
frontend/  Next.js (App Router) + shadcn/ui, Persian RTL, Vazirmatn
```

The **three test seams** the PRD calls for are established here:

1. **LLM gateway** (`backend/app/llm/`) — one interface (`extract_jd`,
   `extract_resume`, `judge_skill`) with a `FakeLLMGateway` for tests and a
   `LiteLLMGateway` for production (provider-agnostic via `.env`). Injected as a
   FastAPI dependency, so every test runs with no real model call.
2. **Scorer** (`backend/app/scoring/`) — a pure function `(JD requirements,
   per-skill judgments, resume fields, weights) → Match Score + breakdown`. No
   I/O, no model call: same inputs always yield the same ranking, so the
   ranking is auditable. Unit-tested directly over crafted inputs.
3. **HTTP API** — FastAPI `TestClient` behavior tests (`backend/tests/`).

## Prerequisites

- Python ≥ 3.11 (the backend pins 3.12 via `uv`)
- Node ≥ 18
- [`uv`](https://docs.astral.sh/uv/) for the Python environment

## Backend

```bash
cd backend
uv venv --python 3.12 .venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Run the tests (fake gateway, in-memory SQLite — no network):
python -m pytest

# Run the API (http://localhost:8000, docs at /docs):
uvicorn app.main:app --reload
```

Configuration is read from `.env` (copy `.env.example`). The walking skeleton
never calls a model, so no API key is required to run or test it; the LLM
settings exist so the provider can be swapped later with no code change.

## Evaluation (Issue #6)

How we know the ranking works: the harness runs the real scoring pipeline over a
committed Persian **Gold Set** (`backend/app/eval/gold_set.json` — one JD + 10
human-labeled resumes graded 0–3) and reports **Precision@3** and **nDCG** of the
system ranking against the human labels.

```bash
cd backend
source .venv/bin/activate

python -m app.eval          # fake gateway — deterministic, reproducible (CI)
python -m app.eval --real   # real provider via .env — the headline number
```

Reproducible baseline against the **fake gateway** (the engineered Gold Set is
ranked ideally by skill coverage, so this is a fixed CI number, asserted in
`tests/test_eval_harness.py`):

```
Precision@3: 1.000
nDCG:        1.000
```

The fake gateway judges skills by naive substring presence; the **headline
number** comes from `--real`, where the model judges Persian/English skill
variants semantically. The metric functions (`app/eval/metrics.py`) are pure and
unit-tested independently.

## Demo mode (Issue #7)

For a live demo without depending on a model provider, seed the database with a
realistic Persian JD + resumes whose Evaluations are **pre-computed and stored**:

```bash
cd backend
source .venv/bin/activate

python -m app.seed     # loads one JD + ~10 resumes + stored Evaluations
```

Then start the backend and open the HR dashboard — the ranked candidate list
renders from stored data with **no live model call** (`GET /ranking` reads only
stored Evaluations). The seed uses the deterministic fake gateway, so it works
**with the model provider unreachable**, and produces a clear, defensible top
candidate. Re-running the seed replaces the demo JD (idempotent).

To prove the pipeline live, the ranking panel's **«رتبه‌بندی زنده» ("rank now")**
button calls `POST /api/jobs/{id}/rank`, which re-judges every skill through the
gateway and re-scores on demand.

## Frontend

```bash
cd frontend
npm install

# Run the dev server (http://localhost:3000):
npm run dev
```

The frontend proxies `/api/*` to the backend (`http://localhost:8000` by
default; override with `BACKEND_URL`). Start the backend first, then open
<http://localhost:3000> to create and list Job Descriptions.

## Project layout

```
backend/
  app/
    main.py            FastAPI app factory + CORS + lifespan (create tables)
    config.py          Settings from .env (DB + LLM provider)
    db.py              SQLite engine, session, get_db dependency
    models.py          ORM: JobDescription, Submission, Evaluation
    schemas.py         Pydantic request/response
    deps.py            get_gateway() — the injectable LLM seam
    api/jobs.py        create (+extract) / list / get / PATCH requirements (re-scores)
    api/submissions.py applicant submit (+extract +score) / list per JD
    api/ranking.py     GET ranked candidates (stored, no model) / POST rank (live)
    seed.py            `python -m app.seed` — demo JD + resumes + stored Evaluations
    extraction/
      normalize.py     Persian/Arabic digit → Latin folding
      service.py       extract_jd_requirements / extract_resume_fields
    scoring/
      weights.py       ScoreWeights + shipped defaults
      scorer.py        score() — the pure deterministic scorer (Seam 2)
      service.py       per-skill judgments (LLM) → score → persist Evaluation
    eval/
      gold_set.json    committed Persian Gold Set (1 JD + 10 labeled resumes)
      metrics.py       Precision@k / nDCG — pure functions
      harness.py       run the pipeline over the Gold Set → metrics
      __main__.py      `python -m app.eval [--real]`
    llm/
      gateway.py       LLMGateway abstract interface
      fake.py          FakeLLMGateway (tests / offline)
      litellm_gateway.py  LiteLLMGateway (production, lazy imports)
      types.py         JDRequirements, ResumeFields, SkillJudgment
  tests/
    test_jobs_api.py            Seam 3 — create JD → appears in list
    test_gateway.py             Seam 1 — gateway interface + fake
    test_normalize.py           digit normalization (pure)
    test_extraction_service.py  normalize→extract→validate
    test_jd_extraction_api.py   extract on create, review/edit, graceful fail
    test_submissions_api.py     submit → stored with fields, scoping, graceful
    test_scorer.py              Seam 2 — pure scorer: coverage, experience, weights
    test_ranking_api.py         submit → ranked best-first, breakdown, synonyms
    test_eval_metrics.py        pure Precision@k / nDCG
    test_eval_harness.py        Gold Set eval: reproducible P@3 / nDCG
    test_seed.py                demo seed: JD + resumes + stored Evaluations, offline
    test_rank_now_api.py        "rank now" re-runs scoring live, best-first
frontend/
  src/app/             RTL layout + nav (Vazirmatn); / HR dashboard, /apply applicant
  src/components/      Create-JD form, JD list, requirements editor, ranking panel, header, ui/
  src/lib/api.ts       Backend client
```
