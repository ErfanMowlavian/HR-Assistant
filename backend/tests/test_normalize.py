"""Persian/Arabic digit normalization (pure unit tests)."""

from __future__ import annotations

from app.extraction.normalize import normalize_digits


def test_persian_digits_folded_to_latin():
    assert normalize_digits("۵ سال تجربه") == "5 سال تجربه"
    assert normalize_digits("۰۱۲۳۴۵۶۷۸۹") == "0123456789"


def test_arabic_indic_digits_folded_to_latin():
    assert normalize_digits("٥ سنوات") == "5 سنوات"
    assert normalize_digits("٠١٢٣٤٥٦٧٨٩") == "0123456789"


def test_latin_digits_and_letters_untouched():
    assert normalize_digits("React 18 و Python 3") == "React 18 و Python 3"


def test_mixed_text_only_digits_change():
    assert normalize_digits("حداقل ۳ سال با Django") == "حداقل 3 سال با Django"
