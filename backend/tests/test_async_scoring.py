"""Async scoring (ADR-0013): the resume is saved and returned instantly as
"processing"; the slow LLM work runs in a background task that flips it to
"done". Applicants never block on the model, so the request can't outlive a
proxy timeout.

TestClient runs background tasks synchronously as part of the response
lifecycle, so by the time a call returns the scoring has completed — we assert
the create response is "processing" and a follow-up read is "done".
"""

from __future__ import annotations

import app.api.submissions as submissions_api
from app.deps import get_gateway
from app.llm.fake import FakeLLMGateway


def _use_gateway(client, gateway) -> None:
    client.app.dependency_overrides[get_gateway] = lambda: gateway


def _make_job(client) -> int:
    return client.post("/api/jobs", json={"title": "بک‌اند", "text": "متن"}).json()["id"]


def test_create_returns_processing_then_scoring_completes(client):
    _use_gateway(client, FakeLLMGateway())
    job_id = _make_job(client)

    created = client.post(
        f"/api/jobs/{job_id}/submissions",
        json={"applicant_name": "سارا", "resume_text": "مسلط به Python و FastAPI و React."},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "processing"  # instant response, no model wait
    assert body["resume_fields"] is None  # not extracted yet on this response

    polled = client.get(f"/api/jobs/{job_id}/submissions/{body['id']}").json()
    assert polled["status"] == "done"
    assert polled["extraction_ok"] is True
    assert polled["resume_fields"]["skills"]

    # And it now appears in the ranking with a stored evaluation.
    ranking = client.get(f"/api/jobs/{job_id}/ranking").json()
    assert ranking[0]["evaluation"] is not None


def test_unexpected_scoring_error_marks_failed(client, monkeypatch):
    # The worker defensively swallows gateway errors, so "failed" is the
    # safety net for a genuinely unexpected (non-gateway) error. Simulate one
    # and assert the submission ends "failed" rather than stuck on "processing".
    _use_gateway(client, FakeLLMGateway())
    job_id = _make_job(client)

    def _boom(*_args, **_kwargs):
        raise RuntimeError("unexpected worker failure")

    monkeypatch.setattr(submissions_api, "extract_resume_fields", _boom)

    created = client.post(
        f"/api/jobs/{job_id}/submissions",
        json={"applicant_name": "خطا", "resume_text": "رزومه"},
    )
    assert created.status_code == 201
    polled = client.get(f"/api/jobs/{job_id}/submissions/{created.json()['id']}").json()
    assert polled["status"] == "failed"


def test_get_missing_submission_is_404(client):
    job_id = _make_job(client)
    assert client.get(f"/api/jobs/{job_id}/submissions/9999").status_code == 404
