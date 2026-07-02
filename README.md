# HR Assistant — Persian Resume Ranking (MVP)

A Persian, right-to-left web app that ranks résumés against a Job Description.
The **LLM reads** (extracts structured fields, judges each skill yes/partial/no)
and **deterministic math ranks** — explainable by design.

> **فارسی:** [README.fa.md](README.fa.md) — مستندات کامل پروژه به زبان فارسی

---

## Live Demo (Quick Walkthrough)

> Runs with pre-computed demo data — no live AI API needed.

**Demo flow (under 3 minutes):**

1. **Dashboard** — Open the HR dashboard showing the list of Job Descriptions
2. **Create a JD** — Enter a new job title and description
3. **Submit a Résumé** — On the applicant page, paste or upload a résumé
4. **View Ranking** — Go back to the dashboard — candidates are ranked best-match-first
5. **Score Breakdown** — Click any candidate to see the per-skill score breakdown
6. **Gap Report** — Applicants can see which required skills their résumé doesn't demonstrate

> Run with one command: `docker compose up --build`  
> Load demo data: `docker compose exec backend python -m app.seed`

---

## Project Topic

**Persian Resume Ranking System (HR Assistant)** — an RTL web application that uses AI to rank résumés against job descriptions.

## Scenario

A tech company receives dozens of résumés for an open position. The HR specialist, instead of manually reading each résumé and guessing the fit, uses this system:

1. **Create Job Description** — HR enters the job description
2. **Auto-extraction** — AI extracts required skills, experience, education, seniority
3. **Submit Résumé** — applicants submit their résumé (text or PDF)
4. **Smart Scoring** — the system scores each résumé against the JD
5. **Ranking** — résumés displayed best-match-first

## Project Goals

| Goal | Description |
|------|-------------|
| **Overall goal** | Design and implement a Persian resume ranking system |
| **Specific 1** | Auto-extract job requirements from JD via LLM |
| **Specific 2** | Accept résumés (text & PDF) and extract structured fields |
| **Specific 3** | Deterministic, transparent scoring per résumé |
| **Specific 4** | Explainable ranking of candidates |
| **Specific 5** | Read-only Gap report for applicants |
| **Specific 6** | Evaluate ranking quality with Precision@3 and nDCG |
| **Specific 7** | Demo mode with pre-computed data (no live API needed) |

## Target Community

| Stakeholder | Role | Primary Need |
|-------------|------|-------------|
| **HR Specialist** | Primary admin user | View rankings, inspect scores, edit requirements |
| **Applicant** | Applicant-side user | Submit résumé, view Gap report |
| **IT Manager** | Project sponsor | Deploy system, ensure quality |
| **Developers** | Project team | Maintain and extend the system |

---

## Architecture

```
backend/   FastAPI + SQLite, the LLM-gateway seam, tests
frontend/  Next.js (App Router) + shadcn/ui, Persian RTL, Vazirmatn
```

## Run with Docker

```bash
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend API + docs: http://localhost:8000/docs

Load demo data:
```bash
docker compose exec backend python -m app.seed
```

---

## Further Documentation

| Document | Description |
|----------|-------------|
| [📋 Project Management Plan (Persian)](doc-fa/management-plan.md) | WBS, work packages, time/cost estimation, network diagram, critical path, Gantt, EVM, Trello, MS Project |
| [📄 PRD](docs/prd-resume-ranking.md) | Product requirements document |
| [📖 Glossary](docs/glossary.md) | Domain terminology |
| [🧠 Domain Model](docs/domain-model.md) | Conceptual system model |
| [🏛️ Architecture Decisions](docs/decisions/) | 14 ADRs |
