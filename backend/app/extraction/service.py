"""Schema-constrained extraction of JD requirements via the LLM gateway.

The gateway (Instructor + Pydantic, with retries) guarantees a schema-valid
`JDRequirements`; this layer normalizes Persian digits first and re-validates
the result so malformed model output surfaces as a clean error rather than a
crash deeper in the stack.
"""

from __future__ import annotations

from pydantic import ValidationError

from app.extraction.normalize import normalize_digits
from app.llm.errors import GatewayError, InvalidModelOutput, ProviderUnavailable
from app.llm.gateway import LLMGateway
from app.llm.types import JDRequirements, ResumeFields


def _call(gateway_call, *, label: str):
    """Run a gateway call, mapping its failure onto the seam's vocabulary.

    A gateway adapter already raises a typed `GatewayError`, which we let
    through. Anything else escaping the call is unclassified, so we treat it as
    a transient `ProviderUnavailable` rather than guess it was bad output.
    """
    try:
        return gateway_call()
    except GatewayError:
        raise
    except Exception as exc:
        raise ProviderUnavailable(f"{label}: {exc}") from exc


def extract_jd_requirements(gateway: LLMGateway, text: str) -> JDRequirements:
    """Extract structured requirements from a JD's Persian text.

    Persian/Arabic digits are normalized before the model sees the text so
    numeric fields (e.g. minimum years) are reasoned over correctly (ADR-0004).
    """
    normalized = normalize_digits(text)
    result = _call(lambda: gateway.extract_jd(normalized), label="extract_jd")
    # Re-validate at the boundary: off-schema output is invalid, not transient.
    try:
        return JDRequirements.model_validate(result.model_dump())
    except ValidationError as exc:
        raise InvalidModelOutput(str(exc)) from exc


def extract_resume_fields(gateway: LLMGateway, text: str) -> ResumeFields:
    """Extract structured fields from a resume's Persian text.

    Same normalize-then-extract-then-validate shape as JD extraction; the raw
    resume text is stored separately so mixed Persian/English skill text is
    preserved for per-skill judgment (#5).
    """
    normalized = normalize_digits(text)
    result = _call(lambda: gateway.extract_resume(normalized), label="extract_resume")
    try:
        return ResumeFields.model_validate(result.model_dump())
    except ValidationError as exc:
        raise InvalidModelOutput(str(exc)) from exc
