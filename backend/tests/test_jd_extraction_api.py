"""Seam 3 — JD requirement extraction + HR review (behavior tests, fake gateway).

No real model call: the gateway is overridden per-test with a fake (or a
deliberately broken) implementation.
"""

from __future__ import annotations

from app.deps import get_gateway
from app.llm.fake import FakeLLMGateway
from app.llm.gateway import LLMGateway
from app.llm.types import JDRequirements, ResumeFields, SkillJudgment, SkillVerdict


def _use_gateway(client, gateway: LLMGateway) -> None:
    client.app.dependency_overrides[get_gateway] = lambda: gateway


def test_creating_jd_extracts_requirements(client):
    canned = JDRequirements(
        required_skills=["Python", "FastAPI"],
        nice_to_have_skills=["React"],
        min_years_experience=3,
        education="کارشناسی",
        seniority="senior",
    )
    _use_gateway(client, FakeLLMGateway(jd=canned))

    body = client.post(
        "/api/jobs",
        json={"title": "بک‌اند", "text": "حداقل ۳ سال تجربه با Python."},
    ).json()

    assert body["extraction_ok"] is True
    assert body["requirements"]["required_skills"] == ["Python", "FastAPI"]
    assert body["requirements"]["min_years_experience"] == 3
    assert body["requirements"]["seniority"] == "senior"


def test_requirements_visible_via_get(client):
    job_id = client.post("/api/jobs", json={"title": "نقش", "text": "متن"}).json()["id"]
    fetched = client.get(f"/api/jobs/{job_id}").json()
    assert fetched["id"] == job_id
    assert fetched["requirements"] is not None


def test_hr_can_review_and_edit_requirements(client):
    job_id = client.post("/api/jobs", json={"title": "نقش", "text": "متن"}).json()["id"]

    corrected = {
        "required_skills": ["Go", "Kubernetes"],
        "nice_to_have_skills": ["Terraform"],
        "min_years_experience": 5,
        "education": "کارشناسی ارشد",
        "seniority": "lead",
    }
    patched = client.patch(f"/api/jobs/{job_id}/requirements", json=corrected)
    assert patched.status_code == 200
    assert patched.json()["requirements"] == corrected

    # The correction persists.
    assert client.get(f"/api/jobs/{job_id}").json()["requirements"] == corrected


def test_edit_rejects_invalid_requirements(client):
    job_id = client.post("/api/jobs", json={"title": "نقش", "text": "متن"}).json()["id"]
    # min_years_experience must be an int, not arbitrary text.
    resp = client.patch(
        f"/api/jobs/{job_id}/requirements",
        json={"min_years_experience": "خیلی"},
    )
    assert resp.status_code == 422


class _BrokenGateway(LLMGateway):
    """Simulates exhausted Instructor retries / an unreachable provider."""

    def extract_jd(self, text: str) -> JDRequirements:
        raise RuntimeError("model unreachable")

    def extract_resume(self, text: str) -> ResumeFields:  # pragma: no cover
        raise RuntimeError("model unreachable")

    def judge_skill(self, skill: str, resume_text: str) -> SkillJudgment:  # pragma: no cover
        raise RuntimeError("model unreachable")


def test_failed_extraction_is_graceful_not_a_crash(client):
    _use_gateway(client, _BrokenGateway())

    resp = client.post("/api/jobs", json={"title": "نقش", "text": "متن"})

    # JD is still created (text not lost); requirements null and flagged.
    assert resp.status_code == 201
    body = resp.json()
    assert body["requirements"] is None
    assert body["extraction_ok"] is False
    # And it is listed, so HR can re-run extraction / fill by hand.
    assert any(j["id"] == body["id"] for j in client.get("/api/jobs").json())


def test_get_missing_jd_returns_404(client):
    assert client.get("/api/jobs/9999").status_code == 404
