"""SQLite persistence: engine, session factory, and the FastAPI DB dependency."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def _tune_sqlite(dbapi_connection, _record) -> None:
    """Make SQLite tolerant of concurrent writers (many applicants at once).

    The default rollback journal allows only one connection to touch the
    database at a time, and a writer that finds it busy fails immediately with
    "database is locked". Two pragmas fix that for our workload:

    - WAL lets readers run concurrently with a writer (no reader blocks).
    - busy_timeout makes a writer *wait* up to N ms for the lock instead of
      erroring on the spot — so overlapping submissions queue rather than 500.
    """
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")  # 30s
    cursor.close()


def make_engine(database_url: str | None = None):
    url = database_url or get_settings().database_url
    # check_same_thread=False lets the SQLite connection be shared across the
    # threads FastAPI/Starlette uses for sync endpoints.
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine = create_engine(url, connect_args=connect_args)
    if url.startswith("sqlite"):
        event.listen(engine, "connect", _tune_sqlite)
    return engine


engine = make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """Create tables. Models must be imported before this runs."""
    from app import models  # noqa: F401  (register mappers)

    Base.metadata.create_all(bind=engine)
    _add_submission_status_column(engine)


def _add_submission_status_column(bind) -> None:
    """Additive migration: databases created before async scoring lack
    submissions.status. Add it, defaulting existing rows to 'done' (they were
    scored synchronously at submit time). No-op once the column exists.
    """
    from sqlalchemy import inspect, text

    inspector = inspect(bind)
    if "submissions" not in inspector.get_table_names():
        return
    columns = {c["name"] for c in inspector.get_columns("submissions")}
    if "status" not in columns:
        with bind.begin() as conn:
            conn.execute(
                text(
                    "ALTER TABLE submissions "
                    "ADD COLUMN status VARCHAR(16) NOT NULL DEFAULT 'done'"
                )
            )


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_sessionmaker() -> sessionmaker:
    """FastAPI dependency returning the session *factory*.

    Background tasks outlive the request (and its `get_db` session is closed
    when the response is sent), so they must open their own session. Injecting
    the factory — rather than importing `SessionLocal` directly — keeps the
    background worker pointed at whatever database the request used, which lets
    tests override it onto their isolated DB.
    """
    return SessionLocal
