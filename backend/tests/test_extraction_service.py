"""The extraction service: normalize-then-extract, and boundary validation."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.extraction.service import extract_jd_requirements
from app.llm.errors import GatewayError, InvalidModelOutput, ProviderUnavailable
from app.llm.fake import FakeLLMGateway
from app.llm.gateway import LLMGateway
from app.llm.types import JDRequirements, ResumeFields, SkillJudgment


class _SpyGateway(FakeLLMGateway):
    """Records the text actually passed to the model."""

    def __init__(self) -> None:
        super().__init__()
        self.seen_text: str | None = None

    def extract_jd(self, text: str) -> JDRequirements:
        self.seen_text = text
        return super().extract_jd(text)


def test_digits_are_normalized_before_the_model_sees_them():
    spy = _SpyGateway()
    extract_jd_requirements(spy, "حداقل ۵ سال تجربه با Python")
    assert spy.seen_text == "حداقل 5 سال تجربه با Python"


def test_returns_schema_valid_requirements():
    result = extract_jd_requirements(FakeLLMGateway(), "متن شرح شغل")
    assert isinstance(result, JDRequirements)


class _Gateway(LLMGateway):
    """A gateway whose extract_jd raises or returns whatever a test supplies."""

    def __init__(self, on_extract_jd) -> None:
        self._on_extract_jd = on_extract_jd

    def extract_jd(self, text: str):
        return self._on_extract_jd()

    def extract_resume(self, text: str) -> ResumeFields:  # pragma: no cover
        raise NotImplementedError

    def judge_skill(self, skill: str, resume_text: str) -> SkillJudgment:  # pragma: no cover
        raise NotImplementedError


def _raise(exc):
    def _f():
        raise exc

    return _f


def test_unclassified_gateway_exception_becomes_provider_unavailable():
    # A raw, untyped exception from the gateway is treated as transient.
    with pytest.raises(ProviderUnavailable):
        extract_jd_requirements(_Gateway(_raise(ConnectionError("boom"))), "متن")


def test_typed_gateway_error_propagates_unchanged():
    # An adapter that already classified its failure is not reclassified.
    err = InvalidModelOutput("off schema")
    with pytest.raises(InvalidModelOutput):
        extract_jd_requirements(_Gateway(_raise(err)), "متن")
    # And it's still catchable as the base, for graceful degradation.
    assert isinstance(err, GatewayError)


def test_off_schema_output_at_the_boundary_is_invalid_model_output():
    # Gateway returns something whose model_dump fails JDRequirements validation.
    bad = SimpleNamespace(model_dump=lambda: {"min_years_experience": "not-an-int"})
    with pytest.raises(InvalidModelOutput):
        extract_jd_requirements(_Gateway(lambda: bad), "متن")
