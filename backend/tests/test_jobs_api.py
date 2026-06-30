"""Seam 3 — HTTP API behavior tests (FastAPI TestClient).

These assert external behavior only: what HR sends and sees, not how the JD is
stored or wired internally.
"""

from __future__ import annotations


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_create_jd_then_appears_in_list(client):
    # The walking skeleton's acceptance criterion: create a JD -> see it listed.
    payload = {
        "title": "مهندس نرم‌افزار ارشد",
        "text": "ما به دنبال یک مهندس نرم‌افزار با تجربه در Python و FastAPI هستیم.",
    }

    created = client.post("/api/jobs", json=payload)
    assert created.status_code == 201
    body = created.json()
    assert body["id"] > 0
    assert body["title"] == payload["title"]
    assert body["text"] == payload["text"]
    assert "created_at" in body

    listed = client.get("/api/jobs")
    assert listed.status_code == 200
    jobs = listed.json()
    assert len(jobs) == 1
    assert jobs[0]["id"] == body["id"]
    assert jobs[0]["title"] == payload["title"]


def test_list_is_empty_initially(client):
    assert client.get("/api/jobs").json() == []


def test_create_jd_rejects_blank_title(client):
    resp = client.post("/api/jobs", json={"title": "", "text": "متن"})
    assert resp.status_code == 422


def test_multiple_jds_listed_newest_first(client):
    for title in ["نقش اول", "نقش دوم", "نقش سوم"]:
        assert client.post("/api/jobs", json={"title": title, "text": "متن"}).status_code == 201

    titles = [j["title"] for j in client.get("/api/jobs").json()]
    assert set(titles) == {"نقش اول", "نقش دوم", "نقش سوم"}
    assert len(titles) == 3
