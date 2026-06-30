"""Seam 3 — scoring + ranked HR dashboard (behavior tests, fake gateway).

Exercises the real flow: create a JD with requirements → applicants submit →
HR opens the JD's ranking and sees candidates ordered best-match first, each
with a breakdown and per-skill yes/partial/no judgments.
"""

from __future__ import annotations

from app.deps import get_gateway
from app.llm.fake import FakeLLMGateway
from app.llm.types import JDRequirements, ResumeFields, SkillVerdict


def _use_gateway(client, gateway) -> None:
    client.app.dependency_overrides[get_gateway] = lambda: gateway


def _make_job(client) -> int:
    # The fake's default JD requires Python + FastAPI, nice-to-have React.
    return client.post("/api/jobs", json={"title": "بک‌اند", "text": "متن"}).json()["id"]


def _submit(client, job_id: int, name: str, resume: str) -> dict:
    return client.post(
        f"/api/jobs/{job_id}/submissions",
        json={"applicant_name": name, "resume_text": resume},
    ).json()


def test_candidates_ranked_best_match_first(client):
    # Default fake gateway judges by substring presence in the resume text, so
    # what each candidate "wrote" drives their coverage and thus their rank.
    _use_gateway(client, FakeLLMGateway())
    job_id = _make_job(client)

    _submit(client, job_id, "ضعیف", "تجربه عمومی بدون فناوری خاص.")
    _submit(client, job_id, "متوسط", "کار با Python.")
    _submit(client, job_id, "قوی", "مسلط به Python و FastAPI و React.")

    ranking = client.get(f"/api/jobs/{job_id}/ranking").json()
    names = [c["applicant_name"] for c in ranking]
    assert names == ["قوی", "متوسط", "ضعیف"]

    scores = [c["evaluation"]["match_score"] for c in ranking]
    assert scores[0] > scores[1] > scores[2]


def test_ranked_candidate_exposes_breakdown_and_per_skill_judgments(client):
    _use_gateway(client, FakeLLMGateway())
    job_id = _make_job(client)
    _submit(client, job_id, "قوی", "مسلط به Python و FastAPI و React.")

    top = client.get(f"/api/jobs/{job_id}/ranking").json()[0]
    evaluation = top["evaluation"]

    # Breakdown: every criterion present, with a Persian label and a weight.
    keys = {c["key"] for c in evaluation["components"]}
    assert keys == {"required_skills", "nice_to_have_skills", "experience", "education"}
    assert all(c["label"] for c in evaluation["components"])

    # Per-skill judgments cover required + nice-to-have, each yes/partial/no.
    judged = {j["skill"]: j["verdict"] for j in evaluation["judgments"]}
    assert judged["Python"] == "yes"
    assert judged["FastAPI"] == "yes"
    assert judged["React"] == "yes"
    assert {j["kind"] for j in evaluation["judgments"]} == {"required", "nice"}


def test_persian_and_english_skill_synonyms_match(client):
    # The resume names the skill in Persian ("ری‌اکت"); the JD names it in
    # English ("React"). String matching would miss this — the gateway judgment
    # does not. We model that by mapping the verdict explicitly.
    jd = JDRequirements(required_skills=["React"], nice_to_have_skills=[])
    gateway = FakeLLMGateway(jd=jd, judgments={"React": SkillVerdict.YES})
    _use_gateway(client, gateway)

    job_id = _make_job(client)
    _submit(client, job_id, "سارا", "مسلط به ری‌اکت و توسعهٔ رابط کاربری.")

    top = client.get(f"/api/jobs/{job_id}/ranking").json()[0]
    assert top["evaluation"]["match_score"] == 1.0
    assert top["evaluation"]["judgments"][0]["verdict"] == "yes"


def test_editing_requirements_re_evaluates_submissions(client):
    _use_gateway(client, FakeLLMGateway())
    job_id = _make_job(client)
    _submit(client, job_id, "نامزد", "مسلط به Go و Rust.")  # matches default reqs poorly

    before = client.get(f"/api/jobs/{job_id}/ranking").json()[0]["evaluation"]
    assert before["match_score"] < 1.0

    # HR corrects the requirements to skills this candidate actually has.
    client.patch(
        f"/api/jobs/{job_id}/requirements",
        json={
            "required_skills": ["Go", "Rust"],
            "nice_to_have_skills": [],
            "min_years_experience": 0,
            "education": None,
            "seniority": None,
        },
    )

    after = client.get(f"/api/jobs/{job_id}/ranking").json()[0]["evaluation"]
    assert after["match_score"] == 1.0  # re-scored against the new requirements


def test_unscored_submission_sorts_after_scored_ones(client):
    # A JD whose extraction failed has no requirements, so its submissions are
    # stored but not yet scored.
    class _NoJD(FakeLLMGateway):
        def extract_jd(self, text: str) -> JDRequirements:
            raise RuntimeError("jd extraction down")

    _use_gateway(client, _NoJD())
    job_id = _make_job(client)  # created with requirements=None
    _submit(client, job_id, "بدون‌ارزیابی", "رزومه")

    candidate = client.get(f"/api/jobs/{job_id}/ranking").json()[0]
    assert candidate["evaluation"] is None


def test_ranking_for_missing_jd_is_404(client):
    assert client.get("/api/jobs/9999/ranking").status_code == 404
