"""The extraction service: normalize-then-extract, and boundary validation."""

from __future__ import annotations

import pytest

from app.extraction.service import ExtractionError, extract_jd_requirements
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


class _RaisingGateway(LLMGateway):
    def extract_jd(self, text: str) -> JDRequirements:
        raise ValueError("unparseable model output")

    def extract_resume(self, text: str) -> ResumeFields:  # pragma: no cover
        raise NotImplementedError

    def judge_skill(self, skill: str, resume_text: str) -> SkillJudgment:  # pragma: no cover
        raise NotImplementedError


def test_provider_failure_becomes_extraction_error():
    with pytest.raises(ExtractionError):
        extract_jd_requirements(_RaisingGateway(), "متن")
