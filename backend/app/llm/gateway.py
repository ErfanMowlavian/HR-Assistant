"""The LLM gateway interface — one abstract base, three methods.

All model interaction goes through this seam. Concrete implementations:
`FakeLLMGateway` (tests, deterministic) and `LiteLLMGateway` (production).
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.llm.types import JDRequirements, ResumeFields, SkillJudgment


class LLMGateway(ABC):
    """Provider-agnostic interface for every model call in the system."""

    @abstractmethod
    def extract_jd(self, text: str) -> JDRequirements:
        """Extract structured requirements from a Job Description's text."""

    @abstractmethod
    def extract_resume(self, text: str) -> ResumeFields:
        """Extract structured fields from a resume's text."""

    @abstractmethod
    def judge_skill(self, skill: str, resume_text: str) -> SkillJudgment:
        """Judge one required skill against a resume: yes / partial / no."""
