"""Regression: concurrent applicants must not collide on the SQLite write lock.

The bug (500 "database is locked"): each submission makes multi-second LLM calls
(extraction + per-skill judging). When that work ran *inside* the write
transaction, SQLite — single-writer — serialized overlapping submissions until
they timed out. The fix computes all LLM work before opening the transaction
(so the lock is held only for the quick write) and enables WAL + busy_timeout.

These tests use a real file-based DB (the in-memory StaticPool harness shares
one connection and so can't surface lock contention) and a gateway whose judging
blocks on a barrier, guaranteeing the two requests overlap.
"""

from __future__ import annotations

import threading
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.db import Base, get_db, get_sessionmaker, make_engine
from app.deps import get_gateway
from app.llm.fake import FakeLLMGateway
from app.llm.types import SkillJudgment
from app.main import create_app


class BarrierGateway(FakeLLMGateway):
    """A fake gateway whose skill-judging blocks until both threads arrive.

    Forces the two in-flight submissions to overlap precisely while judging —
    the window in which the old code held the write lock across network I/O.
    """

    def __init__(self, parties: int) -> None:
        super().__init__()
        self._barrier = threading.Barrier(parties, timeout=10)

    def judge_skill(self, skill: str, resume_text: str) -> SkillJudgment:
        self._barrier.wait()  # both submissions are now mid-judging together
        return super().judge_skill(skill, resume_text)


@pytest.fixture
def file_client(tmp_path) -> Iterator[TestClient]:
    """A TestClient backed by a real on-disk SQLite DB (one engine, WAL +
    busy_timeout from `make_engine`), shared across worker threads."""
    db_path = tmp_path / "concurrency.db"
    engine = make_engine(f"sqlite:///{db_path}")
    TestingSession = sessionmaker(
        bind=engine, autoflush=False, expire_on_commit=False
    )
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    gateway = BarrierGateway(parties=2)
    app = create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_sessionmaker] = lambda: TestingSession
    app.dependency_overrides[get_gateway] = lambda: gateway

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()
    engine.dispose()


def _make_job_with_requirements(client: TestClient) -> int:
    job = client.post(
        "/api/jobs", json={"title": "مهندس", "text": "Python و FastAPI"}
    ).json()
    client.patch(
        f"/api/jobs/{job['id']}/requirements",
        json={
            "required_skills": ["Python", "FastAPI"],
            "nice_to_have_skills": [],
            "min_years_experience": 0,
            "education": None,
            "seniority": None,
        },
    )
    return job["id"]


def test_two_simultaneous_submissions_both_succeed(file_client: TestClient) -> None:
    job_id = _make_job_with_requirements(file_client)

    results: dict[int, int] = {}

    def submit(i: int) -> None:
        resp = file_client.post(
            f"/api/jobs/{job_id}/submissions",
            json={
                "applicant_name": f"متقاضی {i}",
                "resume_text": "Python and FastAPI developer.",
            },
        )
        results[i] = resp.status_code

    threads = [threading.Thread(target=submit, args=(i,)) for i in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Neither applicant gets a 500 "database is locked"; both are created.
    assert results == {0: 201, 1: 201}

    ranking = file_client.get(f"/api/jobs/{job_id}/ranking").json()
    assert len(ranking) == 2
    assert all(c["evaluation"] is not None for c in ranking)


def test_sqlite_engine_uses_wal_and_busy_timeout(tmp_path) -> None:
    """The pragmas that let writers wait instead of erroring are actually set."""
    from sqlalchemy import text

    engine = make_engine(f"sqlite:///{tmp_path / 'pragma.db'}")
    with engine.connect() as conn:
        journal_mode = conn.execute(text("PRAGMA journal_mode")).scalar()
        busy_timeout = conn.execute(text("PRAGMA busy_timeout")).scalar()
    engine.dispose()

    assert journal_mode == "wal"
    assert busy_timeout == 30000
