"""Persian/Arabic digit normalization (ADR-0004).

Persian text writes numbers with Persian (۰-۹) or Arabic-Indic (٠-٩) digits.
They must be folded to Latin (0-9) before any numeric reasoning, so that
"۵ سال" is understood as 5 years.

A general text utility, not tied to any one layer: extraction normalizes the
text the model reads, and the scorer folds extracted values before matching.
It lives here, at the top level, so neither consumer imports the other's package.
"""

from __future__ import annotations

# U+06F0..U+06F9 (Persian) and U+0660..U+0669 (Arabic-Indic) -> '0'..'9'.
_DIGIT_MAP = {ord(p): ord("0") + i for i, p in enumerate("۰۱۲۳۴۵۶۷۸۹")}
_DIGIT_MAP.update({ord(a): ord("0") + i for i, a in enumerate("٠١٢٣٤٥٦٧٨٩")})


def normalize_digits(text: str) -> str:
    """Return `text` with Persian/Arabic-Indic digits folded to Latin 0-9.

    Non-digit characters (including Persian letters) are left untouched.
    """
    return text.translate(_DIGIT_MAP)
