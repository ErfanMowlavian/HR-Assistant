"""The gateway adapter's failure classifier (Issue: typed extraction errors).

`_classify_gateway_error` is the one place raw provider/parse exceptions are
mapped onto the seam's vocabulary, so it's unit-tested directly rather than
only through a live model call.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError

from app.llm.errors import GatewayError, InvalidModelOutput, ProviderUnavailable
from app.llm.litellm_gateway import _classify_gateway_error


def _a_validation_error() -> ValidationError:
    class M(BaseModel):
        n: int

    try:
        M(n="not-an-int")
    except ValidationError as exc:
        return exc
    raise AssertionError("expected a ValidationError")


def test_pydantic_validation_error_is_invalid_output():
    assert isinstance(_classify_gateway_error(_a_validation_error()), InvalidModelOutput)


def test_instructor_retry_exception_name_is_invalid_output():
    class InstructorRetryException(Exception):
        pass

    assert isinstance(
        _classify_gateway_error(InstructorRetryException("gave up")), InvalidModelOutput
    )


@pytest.mark.parametrize("exc", [ConnectionError("down"), TimeoutError(), RuntimeError("401")])
def test_transport_and_unknown_errors_are_provider_unavailable(exc):
    assert isinstance(_classify_gateway_error(exc), ProviderUnavailable)


def test_already_typed_error_passes_through_unchanged():
    err = ProviderUnavailable("already classified")
    assert _classify_gateway_error(err) is err
    assert isinstance(err, GatewayError)
