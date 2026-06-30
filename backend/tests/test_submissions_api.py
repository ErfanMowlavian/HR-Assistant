"""Seam 3 — applicant submission + resume extraction (behavior tests, fake gateway)."""

from __future__ import annotations

from app.deps import get_gateway
from app.llm.fake import FakeLLMGateway
from app.llm.gateway import LLMGateway
from app.llm.types import JDRequirements, ResumeFields, SkillJudgment


def _use_gateway(client, gateway: LLMGateway) -> None:
    client.app.dependency_overrides[get_gateway] = lambda: gateway


def _make_job(client) -> int:
    return client.post("/api/jobs", json={"title": "نقش", "text": "متن"}).json()["id"]


def test_applicant_submits_resume_and_fields_are_extracted(client):
    canned = ResumeFields(
        skills=["Python", "ری‌اکت"],
        total_years_experience=6.0,
        titles=["مهندس نرم‌افزار"],
        education="کارشناسی",
    )
    _use_gateway(client, FakeLLMGateway(resume=canned))
    job_id = _make_job(client)

    resp = client.post(
        f"/api/jobs/{job_id}/submissions",
        json={"applicant_name": "سارا رضایی", "resume_text": "۶ سال تجربه با Python و ری‌اکت."},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["job_id"] == job_id
    assert body["applicant_name"] == "سارا رضایی"
    # Scoring is async (ADR-0013): create returns immediately as "processing",
    # before the model has run, so fields aren't populated on this response.
    assert body["status"] == "processing"

    # The background task (run synchronously by TestClient) has since extracted
    # the fields; the polled submission reflects the finished result.
    scored = client.get(f"/api/jobs/{job_id}/submissions/{body['id']}").json()
    assert scored["status"] == "done"
    assert scored["extraction_ok"] is True
    assert scored["resume_fields"]["skills"] == ["Python", "ری‌اکت"]
    assert scored["resume_fields"]["total_years_experience"] == 6.0


def test_mixed_script_resume_text_preserved_verbatim(client):
    job_id = _make_job(client)
    raw = "تجربه با React و Django و مهارت‌های نرم مانند کار تیمی."
    sub = client.post(
        f"/api/jobs/{job_id}/submissions",
        json={"applicant_name": "علی", "resume_text": raw},
    ).json()
    # Raw text kept intact for later per-skill judgment (#5).
    assert sub["resume_text"] == raw


def test_submission_linked_and_listed_for_its_jd(client):
    job_id = _make_job(client)
    other_job = _make_job(client)
    client.post(
        f"/api/jobs/{job_id}/submissions",
        json={"applicant_name": "الف", "resume_text": "رزومه"},
    )

    listed = client.get(f"/api/jobs/{job_id}/submissions").json()
    assert len(listed) == 1
    assert listed[0]["applicant_name"] == "الف"
    # The other JD has none — submissions are scoped to their JD.
    assert client.get(f"/api/jobs/{other_job}/submissions").json() == []


def test_submitting_to_missing_jd_is_404(client):
    resp = client.post(
        "/api/jobs/9999/submissions",
        json={"applicant_name": "کسی", "resume_text": "رزومه"},
    )
    assert resp.status_code == 404


def test_blank_resume_rejected(client):
    job_id = _make_job(client)
    resp = client.post(
        f"/api/jobs/{job_id}/submissions",
        json={"applicant_name": "نام", "resume_text": ""},
    )
    assert resp.status_code == 422


class _BrokenGateway(LLMGateway):
    def extract_jd(self, text: str) -> JDRequirements:  # pragma: no cover
        raise RuntimeError("down")

    def extract_resume(self, text: str) -> ResumeFields:
        raise RuntimeError("model unreachable")

    def judge_skill(self, skill: str, resume_text: str) -> SkillJudgment:  # pragma: no cover
        raise RuntimeError("down")


def test_failed_resume_extraction_is_graceful(client):
    job_id = _make_job(client)
    _use_gateway(client, _BrokenGateway())

    resp = client.post(
        f"/api/jobs/{job_id}/submissions",
        json={"applicant_name": "نام", "resume_text": "رزومه"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["resume_fields"] is None
    assert body["extraction_ok"] is False
