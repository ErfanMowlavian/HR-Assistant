"""Typed failures for the LLM gateway seam.

A gateway call fails in two ways that warrant different responses:

- `ProviderUnavailable` — the model couldn't be reached or used (transport,
  auth, timeout, rate limit). Transient: a retry may succeed.
- `InvalidModelOutput` — the model responded, but the output didn't match the
  schema. Retrying the same input won't help; the prompt or input is at fault.

These live with the seam (not the extraction layer) so every adapter's failures
speak one vocabulary and callers can branch on the cause without knowing the
provider. Both subclass `GatewayError`, so a caller that only cares "did it
fail?" catches the base and degrades gracefully.
"""

from __future__ import annotations


class GatewayError(RuntimeError):
    """A gateway call failed. Catch this to degrade gracefully on any cause."""


class ProviderUnavailable(GatewayError):
    """The model couldn't be reached or used (transport / auth / timeout)."""


class InvalidModelOutput(GatewayError):
    """The model responded, but its output was off-schema."""
