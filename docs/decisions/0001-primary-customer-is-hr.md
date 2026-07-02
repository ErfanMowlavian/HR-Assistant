# ADR 0001 — Primary customer is HR, not the applicant

- Status: Accepted
- Date: 2026-06-30

## Context
The product has two possible "hearts": an HR-side tool that ranks resumes
against a job description, and an applicant-side tool that coaches job-seekers
to complete a weak resume. These pull in opposite directions: if the applicant
coach succeeds for everyone, it flattens the very signal the ranker depends on.

## Decision
This is fundamentally an **HR tool**. The single job is: given a job
description and a set of resumes, surface the best-matched candidates quickly
and defensibly. The applicant-side "fill the gaps" feature, if it exists at
all, is secondary and serves data quality for ranking — not the applicant's
career outcomes.

## Consequences
- Success is measured by the quality/usefulness of the ranking to HR, not by
  how much an applicant's resume "improved."
- The applicant-side coaching feature is now in scope-question territory (see
  later ADR): it may be cut, or constrained so it can't be used to game rank.
- Open question carried forward: what does "best match" mean, and how do we
  know a ranking is good? (graded in a later ADR)
