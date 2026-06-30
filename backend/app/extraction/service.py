"""Schema-constrained extraction of JD requirements via the LLM gateway.

The gateway (Instructor + Pydantic, with retries) guarantees a schema-valid
`JDRequirements`; this layer normalizes Persian digits first and re-validates
the result so malformed model output surfaces as a clean error rather than a
crash deeper in the stack.
"""

from __future__ import annotations

from app.extraction.normalize import normalize_digits
from app.llm.gateway import LLMGateway
from app.llm.types import JDRequirements


class ExtractionError(RuntimeError):
    """Raised when extraction fails (provider error or invalid output)."""


def extract_jd_requirements(gateway: LLMGateway, text: str) -> JDRequirements:
    """Extract structured requirements from a JD's Persian text.

    Persian/Arabic digits are normalized before the model sees the text so
    numeric fields (e.g. minimum years) are reasoned over correctly (ADR-0004).
    """
    normalized = normalize_digits(text)
    try:
        result = gateway.extract_jd(normalized)
        # Re-validate at the boundary: even if a gateway hands back something
        # off-schema, we raise ExtractionError instead of propagating raw.
        return JDRequirements.model_validate(result.model_dump())
    except ExtractionError:
        raise
    except Exception as exc:  # provider error, validation failure, timeout…
        raise ExtractionError(str(exc)) from exc
