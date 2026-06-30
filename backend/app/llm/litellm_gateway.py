"""Production gateway: LiteLLM + Instructor, provider-agnostic via .env.

`litellm` and `instructor` are imported lazily so importing this module (and
the app) never requires them and never touches the network. The walking
skeleton does not call these methods; prompt engineering and Persian-digit
normalization land in slices #3–#5. The seam, however, is real today.
"""

from __future__ import annotations

from app.config import Settings, get_settings
from app.llm.gateway import LLMGateway
from app.llm.types import JDRequirements, ResumeFields, SkillJudgment


class LiteLLMGateway(LLMGateway):
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._client = None  # built lazily on first call

    def _instructor_client(self):
        if self._client is None:
            import instructor
            from litellm import completion

            self._client = instructor.from_litellm(completion)
        return self._client

    def _complete(self, response_model, system: str, user: str):
        s = self._settings
        client = self._instructor_client()
        return client.chat.completions.create(
            model=s.llm_model,
            api_key=s.llm_api_key,
            base_url=s.llm_base_url,
            temperature=s.llm_temperature,
            timeout=s.llm_timeout,
            response_model=response_model,
            max_retries=2,  # Instructor re-asks on schema-validation failure
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )

    def extract_jd(self, text: str) -> JDRequirements:
        return self._complete(
            JDRequirements,
            system="استخراج‌گر نیازمندی‌های شرح شغل. خروجی را مطابق طرح بده.",
            user=text,
        )

    def extract_resume(self, text: str) -> ResumeFields:
        return self._complete(
            ResumeFields,
            system="استخراج‌گر فیلدهای رزومه. خروجی را مطابق طرح بده.",
            user=text,
        )

    def judge_skill(self, skill: str, resume_text: str) -> SkillJudgment:
        return self._complete(
            SkillJudgment,
            system=(
                "داوری یک مهارت در برابر رزومه: بله/تاحدی/خیر. "
                "معادل‌های فارسی و انگلیسی یک مهارت یکسان‌اند."
            ),
            user=f"مهارت: {skill}\n\nرزومه:\n{resume_text}",
        )
