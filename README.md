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
2. **Scorer** — a pure function; lands in slice #5.
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
    models.py          ORM: JobDescription, Submission
    schemas.py         Pydantic request/response
    deps.py            get_gateway() — the injectable LLM seam
    api/jobs.py        create (+extract) / list / get / PATCH requirements
    api/submissions.py applicant submit (+extract) / list per JD
    extraction/
      normalize.py     Persian/Arabic digit → Latin folding
      service.py       extract_jd_requirements / extract_resume_fields
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
frontend/
  src/app/             RTL layout + nav (Vazirmatn); / HR dashboard, /apply applicant
  src/components/      Create-JD form, JD list, requirements editor, header, ui/
  src/lib/api.ts       Backend client
```
