# ADR 0004 — Persian-first, RTL, mixed-script

- Status: Accepted
- Date: 2026-06-30

## Context
The product is for a Persian (Farsi) audience: UI, job descriptions, and
resumes are all in Persian. The LLM provider is OpenAI-compatible. Persian
brings RTL layout, font, digit, and PDF-extraction concerns.

## Decision
- **UI is Persian, RTL** (`dir="rtl"`), using the **Vazirmatn** webfont.
- **Resume input is paste-text-first.** PDF upload is best-effort/optional,
  because PDF extraction of Persian (cursive, RTL) is unreliable and can feed
  the LLM garbled text. Paste-text avoids silent ranking corruption.
- **Mixed script is expected.** Tech skills often appear in English inside
  Persian resumes (e.g. "React", "Python") while soft skills are in Persian.
  This is handled by the per-skill LLM judgment design (ADR-0002 refinement),
  not by string matching.
- **Persian digits** (۰-۹) must be normalized to Latin digits before numeric
  reasoning (e.g. years of experience).
- **Example/seed data is Persian** and realistic for the Iranian job market.

## Consequences
- Prompts instruct the LLM to operate over Persian text and may respond in
  Persian where user-facing (e.g. the "what's missing" list) but emit
  structured fields in a stable schema.
- A digit-normalization utility is needed in extraction.
- RTL styling is a real, scheduled task, not an afterthought.
