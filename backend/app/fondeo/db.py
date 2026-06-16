"""Database engine and session management for the funding domain.

SQLite by default — file-based, no server, runs anywhere. The URL is
configurable via FONDEO_DB_URL so production can point at Postgres later and
tests can use an isolated in-memory database.
"""

from __future__ import annotations

import os

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine


def make_engine(url: str | None = None):
    url = url or os.getenv("FONDEO_DB_URL", "sqlite:///fondeo.sqlite")
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    kwargs = {}
    if url == "sqlite://":  # shared in-memory DB (tests)
        kwargs["poolclass"] = StaticPool
    return create_engine(url, connect_args=connect_args, **kwargs)


# Default application engine.
engine = make_engine()


def init_db(eng=None) -> None:
    SQLModel.metadata.create_all(eng or engine)


def get_session():
    """FastAPI dependency yielding a session bound to the default engine."""
    with Session(engine) as session:
        yield session
