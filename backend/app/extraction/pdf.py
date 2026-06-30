"""Best-effort PDF text extraction with a garbled-Persian heuristic (#8).

Persian PDFs frequently extract badly: many producers store glyphs without a
proper Unicode mapping, so `pypdf` returns symbol-soup, replacement characters,
or almost nothing. Paste stays the primary, reliable path; PDF upload is a
convenience. So we extract best-effort and, when the result looks broken, refuse
it and nudge the applicant to paste — rather than silently scoring garbage.
"""

from __future__ import annotations

import io

# A genuine resume has plenty of letters. Garbled extraction is dominated by
# symbols/replacement chars, or comes out nearly empty — these thresholds catch
# the common failure modes without rejecting real (Persian or English) text.
MIN_USABLE_CHARS = 20
LETTER_RATIO_THRESHOLD = 0.5
REPLACEMENT_CHAR = "�"


class PdfExtractionError(Exception):
    """Raised when the bytes can't be parsed as a PDF at all (corrupt/encrypted)."""


def extract_pdf_text(data: bytes) -> str:
    """Extract text from a PDF, best-effort. Raises PdfExtractionError if the
    file can't be opened as a PDF."""
    from pypdf import PdfReader
    from pypdf.errors import PyPdfError

    try:
        reader = PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
    except (PyPdfError, ValueError, OSError) as exc:
        raise PdfExtractionError(str(exc)) from exc
    return "\n".join(pages).strip()


def looks_garbled(text: str) -> bool:
    """True if extracted text looks broken — too short, full of replacement
    characters, or dominated by non-letter symbols.

    Persian letters and Latin letters both count as letters (`str.isalpha`), so
    a clean resume in either language passes; symbol-soup from a bad extraction
    does not. Best-effort, deliberately conservative.
    """
    stripped = text.strip()
    if len(stripped) < MIN_USABLE_CHARS:
        return True
    if REPLACEMENT_CHAR in stripped:
        return True

    non_space = sum(1 for c in stripped if not c.isspace())
    if non_space == 0:
        return True
    letters = sum(1 for c in stripped if c.isalpha())
    return letters / non_space < LETTER_RATIO_THRESHOLD
