"""Best-effort PDF extraction + garbled-Persian heuristic (Issue #8, pure)."""

from __future__ import annotations

from app.extraction.pdf import extract_pdf_text, looks_garbled


def _make_pdf(text: str) -> bytes:
    """Build a minimal valid one-page PDF containing `text` (Latin, Helvetica).

    Offsets and the xref table are computed so pypdf reads it without recovery —
    enough to prove the extract_pdf_text wiring end to end.
    """
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\nBT /F1 24 Tf 72 700 Td (%s) Tj ET\nendstream"
        % (len(text) + 28, text.encode("latin-1")),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"

    xref_pos = len(out)
    out += b"xref\n0 %d\n" % (len(objects) + 1)
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += (
        b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF"
        % (len(objects) + 1, xref_pos)
    )
    return bytes(out)


def test_extract_pdf_text_reads_a_clean_pdf():
    pdf = _make_pdf("Python FastAPI PostgreSQL")
    text = extract_pdf_text(pdf)
    assert "Python" in text and "FastAPI" in text


def test_clean_persian_text_is_not_garbled():
    resume = (
        "مهندس نرم‌افزار با پنج سال تجربه در توسعهٔ بک‌اند با Python و FastAPI. "
        "کارشناسی مهندسی کامپیوتر."
    )
    assert looks_garbled(resume) is False


def test_clean_english_text_is_not_garbled():
    assert looks_garbled("Backend engineer with 5 years of Python and FastAPI.") is False


def test_empty_or_too_short_extraction_is_garbled():
    assert looks_garbled("") is True
    assert looks_garbled("   \n  ") is True
    assert looks_garbled("abc") is True  # below MIN_USABLE_CHARS


def test_replacement_characters_are_garbled():
    assert looks_garbled("مهندس نرم افزار � � � � � � � � � �") is True


def test_symbol_soup_is_garbled():
    # The kind of output a bad Persian PDF produces: mostly non-letter symbols.
    assert looks_garbled("#$%^&*()_+=-[]{};:'\",<>/?\\|~`#$%^&*()_+=") is True
