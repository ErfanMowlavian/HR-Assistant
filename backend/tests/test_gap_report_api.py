"""Seam 3 — read-only applicant Gap Report endpoint (Issue #9).

A gap report is computed from per-skill judgments for a chosen JD + pasted
resume, and is informational only: generating one must never create a
Submission/Evaluation or change any existing ranking.
"""

from __future__ import annotations

from app.deps import get_gateway
from app.llm.fake import FakeLLMGateway


def _use_gateway(client, gateway) -> None:
    client.app.dependency_overrides[get_gateway] = lambda: gateway


def _make_job(client) -> int:
    # Default fake JD: required Python + FastAPI, nice-to-have React.
    return client.post("/api/jobs", json={"title": "بک‌اند", "text": "متن"}).json()["id"]


def test_gap_report_lists_skills_missing_from_resume(client):
    _use_gateway(client, FakeLLMGateway())
    job_id = _make_job(client)

    res = client.post(
        f"/api/jobs/{job_id}/gap-report",
        json={"resume_text": "مسلط به Python."},
    )
    assert res.status_code == 200
    report = res.json()

    assert {g["skill"] for g in report["missing"]} == {"FastAPI", "React"}
    assert report["demonstrated_count"] == 1
    assert report["total_skills"] == 3


def test_gap_report_does_not_create_a_submission_or_change_ranking(client):
    _use_gateway(client, FakeLLMGateway())
    job_id = _make_job(client)

    # A real candidate applies → one stored Evaluation / ranking.
    client.post(
        f"/api/jobs/{job_id}/submissions",
        json={"applicant_name": "قوی", "resume_text": "مسلط به Python و FastAPI و React."},
    )
    before = client.get(f"/api/jobs/{job_id}/ranking").json()

    # An applicant generates gap reports against the same JD.
    client.post(f"/api/jobs/{job_id}/gap-report", json={"resume_text": "فقط Python."})
    client.post(f"/api/jobs/{job_id}/gap-report", json={"resume_text": "هیچ مهارتی."})

    after = client.get(f"/api/jobs/{job_id}/ranking").json()
    # No new submission, and the existing evaluation is byte-for-byte unchanged.
    assert client.get(f"/api/jobs/{job_id}/submissions").json().__len__() == 1
    assert after == before


def test_gap_report_404_for_missing_jd(client):
    _use_gateway(client, FakeLLMGateway())
    res = client.post("/api/jobs/9999/gap-report", json={"resume_text": "متن"})
    assert res.status_code == 404


def test_gap_report_422_when_jd_has_no_requirements(client):
    # JD created while JD-extraction is down → requirements is null.
    from app.llm.types import JDRequirements

    class _NoJD(FakeLLMGateway):
        def extract_jd(self, text: str) -> JDRequirements:
            raise RuntimeError("jd extraction down")

    _use_gateway(client, _NoJD())
    job_id = _make_job(client)

    res = client.post(f"/api/jobs/{job_id}/gap-report", json={"resume_text": "متن"})
    assert res.status_code == 422
