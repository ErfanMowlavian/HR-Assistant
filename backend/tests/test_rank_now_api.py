"""Seam 3 — the "rank now" action (Issue #7).

`POST /api/jobs/{id}/rank` re-runs the scoring pipeline live for every
submission and returns the fresh ranking — the on-demand proof, distinct from
the stored-data read path (`GET /ranking`).
"""

from __future__ import annotations

from app.deps import get_gateway
from app.llm.fake import FakeLLMGateway


def _use_gateway(client, gateway) -> None:
    client.app.dependency_overrides[get_gateway] = lambda: gateway


def _make_job(client) -> int:
    return client.post("/api/jobs", json={"title": "بک‌اند", "text": "متن"}).json()["id"]


def _submit(client, job_id: int, name: str, resume: str) -> None:
    client.post(
        f"/api/jobs/{job_id}/submissions",
        json={"applicant_name": name, "resume_text": resume},
    )


def test_rank_now_returns_candidates_best_match_first(client):
    _use_gateway(client, FakeLLMGateway())
    job_id = _make_job(client)
    _submit(client, job_id, "ضعیف", "تجربه عمومی بدون فناوری خاص.")
    _submit(client, job_id, "قوی", "مسلط به Python و FastAPI و React.")

    res = client.post(f"/api/jobs/{job_id}/rank")
    assert res.status_code == 200
    ranking = res.json()

    names = [c["applicant_name"] for c in ranking]
    assert names == ["قوی", "ضعیف"]
    assert all(c["evaluation"] is not None for c in ranking)
    assert ranking[0]["evaluation"]["match_score"] > ranking[1]["evaluation"]["match_score"]


def test_rank_now_recomputes_against_current_requirements(client):
    # Seed scores with the default fake gateway, then "rank now" with a gateway
    # that judges everything met → every score recomputed to 1.0 live.
    _use_gateway(client, FakeLLMGateway())
    job_id = _make_job(client)
    _submit(client, job_id, "نامزد", "مسلط به Go و Rust.")  # poor under default reqs

    before = client.get(f"/api/jobs/{job_id}/ranking").json()[0]["evaluation"]
    assert before["match_score"] < 1.0

    from app.llm.types import SkillJudgment, SkillVerdict

    class _AllYes(FakeLLMGateway):
        def judge_skill(self, skill: str, resume_text: str) -> SkillJudgment:
            return SkillJudgment(skill=skill, verdict=SkillVerdict.YES)

    _use_gateway(client, _AllYes())
    after = client.post(f"/api/jobs/{job_id}/rank").json()[0]["evaluation"]
    assert after["match_score"] == 1.0


def test_rank_now_for_missing_jd_is_404(client):
    assert client.post("/api/jobs/9999/rank").status_code == 404
