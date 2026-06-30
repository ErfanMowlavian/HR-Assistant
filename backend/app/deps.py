"""Shared FastAPI dependencies — notably the injectable LLM gateway.

Routes depend on `get_gateway`; tests override it with a `FakeLLMGateway` via
`app.dependency_overrides`. This is the single seam that keeps the whole app
testable with no real model call (PRD "Seam 1").
"""

from __future__ import annotations

from functools import lru_cache

from app.llm.gateway import LLMGateway


@lru_cache
def get_gateway() -> LLMGateway:
    # Imported here so the production stack (litellm/instructor) is only
    # touched when a real gateway is actually requested.
    from app.llm.litellm_gateway import LiteLLMGateway

    return LiteLLMGateway()
