"""Seam 1 — the LLM gateway interface and its fake implementation.

Proves the injection seam exists and is honored: the fake conforms to the
interface, returns schema-valid typed results, and is overridable per test.
"""

from __future__ import annotations

import pytest

from app.llm import (
    FakeLLMGateway,
    JDRequirements,
    LLMGateway,
    ResumeFields,
    SkillJudgment,
    SkillVerdict,
)
from app.llm.gateway import LLMGateway as Interface


def test_fake_is_an_llm_gateway():
    assert isinstance(FakeLLMGateway(), LLMGateway)
    assert issubclass(FakeLLMGateway, Interface)


def test_interface_cannot_be_instantiated():
    with pytest.raises(TypeError):
        LLMGateway()  # abstract — must be subclassed


def test_fake_returns_typed_results():
    gw = FakeLLMGateway()
    assert isinstance(gw.extract_jd("شرح شغل"), JDRequirements)
    assert isinstance(gw.extract_resume("رزومه"), ResumeFields)
    assert isinstance(gw.judge_skill("Python", "رزومه"), SkillJudgment)


def test_fake_judgment_is_deterministic():
    gw = FakeLLMGateway()
    assert gw.judge_skill("Python", "تجربه با Python و SQL").verdict is SkillVerdict.YES
    assert gw.judge_skill("Rust", "تجربه با Python و SQL").verdict is SkillVerdict.NO


def test_fake_canned_values_are_overridable():
    canned = JDRequirements(required_skills=["Go"], min_years_experience=7)
    gw = FakeLLMGateway(jd=canned)
    assert gw.extract_jd("هرچیزی").required_skills == ["Go"]
    assert gw.extract_jd("هرچیزی").min_years_experience == 7
