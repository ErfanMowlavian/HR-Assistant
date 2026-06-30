"""Extraction infrastructure: digit normalization + schema-constrained
extraction of structured fields via the LLM gateway.

JD requirement extraction lives here (Issue #3); resume-field extraction (#4)
reuses the same `normalize_digits` + gateway pattern.
"""

from app.extraction.normalize import normalize_digits
from app.extraction.service import extract_jd_requirements

__all__ = ["normalize_digits", "extract_jd_requirements"]
