"""Seam 3 — best-effort PDF upload endpoint (Issue #8).

A clean PDF feeds the same Submission/extraction/scoring path as pasted text;
a garbled or unparseable PDF is refused with a nudge to paste, and crucially
creates no Submission — so a broken PDF never yields a corrupted Evaluation.
"""

from __future__ import annotations

import app.api.submissions as submissions_api
from app.deps import get_gateway
from app.llm.fake import FakeLLMGateway


def _use_gateway(client, gateway) -> None:
    client.app.dependency_overrides[get_gateway] = lambda: gateway


def _make_job(client) -> int:
    return client.post("/api/jobs", json={"title": "بک‌اند", "text": "متن"}).json()["id"]


def _upload(client, job_id: int, name: str = "سارا"):
    return client.post(
        f"/api/jobs/{job_id}/submissions/upload",
        data={"applicant_name": name},
        files={"file": ("resume.pdf", b"%PDF-1.4 fake bytes", "application/pdf")},
    )


def test_clean_pdf_creates_a_usable_submission(client, monkeypatch):
    _use_gateway(client, FakeLLMGateway())
    job_id = _make_job(client)

    monkeypatch.setattr(
        submissions_api,
        "extract_pdf_text",
        lambda data: "مسلط به Python و FastAPI و React با چهار سال تجربه.",
    )

    res = _upload(client, job_id)
    assert res.status_code == 201
    body = res.json()
    # Travels the same path as pasted text: fields extracted, then ranked.
    assert body["extraction_ok"] is True
    ranking = client.get(f"/api/jobs/{job_id}/ranking").json()
    assert len(ranking) == 1
    assert ranking[0]["evaluation"] is not None


def test_garbled_pdf_is_refused_with_paste_nudge_and_creates_nothing(client, monkeypatch):
    _use_gateway(client, FakeLLMGateway())
    job_id = _make_job(client)

    monkeypatch.setattr(
        submissions_api, "extract_pdf_text", lambda data: "#$%^&* � � � ()_+ <<>>"
    )

    res = _upload(client, job_id)
    assert res.status_code == 422
    assert "وارد کنید" in res.json()["detail"]  # nudge to paste

    # No corrupted Evaluation: nothing was persisted.
    assert client.get(f"/api/jobs/{job_id}/submissions").json() == []
    assert client.get(f"/api/jobs/{job_id}/ranking").json() == []


def test_unparseable_pdf_is_refused(client, monkeypatch):
    _use_gateway(client, FakeLLMGateway())
    job_id = _make_job(client)

    def _boom(data):
        from app.extraction.pdf import PdfExtractionError

        raise PdfExtractionError("not a pdf")

    monkeypatch.setattr(submissions_api, "extract_pdf_text", _boom)

    res = _upload(client, job_id)
    assert res.status_code == 422
    assert client.get(f"/api/jobs/{job_id}/submissions").json() == []


def test_upload_to_missing_jd_is_404(client):
    assert _upload(client, 9999).status_code == 404
