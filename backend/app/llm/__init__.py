"""LLM gateway — the single injection seam for all model interaction.

Everything model-dependent depends on the `LLMGateway` interface, never on a
concrete provider. Tests inject `FakeLLMGateway`; production uses
`LiteLLMGateway` (provider-agnostic via `.env`). See ADR-0005 and PRD story #24.
"""

from app.llm.gateway import LLMGateway
from app.llm.fake import FakeLLMGateway
from app.llm.types import (
    JDRequirements,
    ResumeFields,
    SkillJudgment,
    SkillVerdict,
)

__all__ = [
    "LLMGateway",
    "FakeLLMGateway",
    "JDRequirements",
    "ResumeFields",
    "SkillJudgment",
    "SkillVerdict",
]
