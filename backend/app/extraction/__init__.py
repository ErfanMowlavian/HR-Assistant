"""Extraction infrastructure: schema-constrained extraction of structured
fields via the LLM gateway.

JD requirement extraction lives here (Issue #3); resume-field extraction (#4)
reuses the same normalize→gateway→validate pattern. Digit normalization is a
general text utility (`app.normalize`), not extraction-specific.
"""

from app.extraction.service import extract_jd_requirements, extract_resume_fields

__all__ = ["extract_jd_requirements", "extract_resume_fields"]
