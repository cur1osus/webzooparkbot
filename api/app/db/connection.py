from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from api.app.db.models import Base  # noqa: F401 — re-exported for alembic and bootstrap

_DB_USER = os.getenv("DB_USER", "admin_zoopark")
_DB_PASSWORD = os.getenv("DB_PASSWORD", "")
_DB_NAME = os.getenv("DB_NAME", "zoopark")
_DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
_DB_PORT = os.getenv("DB_PORT", "3306")

DATABASE_URL = os.getenv(
    "DB_URL",
    f"mysql+pymysql://{_DB_USER}:{_DB_PASSWORD}@{_DB_HOST}:{_DB_PORT}/{_DB_NAME}?charset=utf8mb4",
)

_engine: Engine | None = None


def _get_engine() -> Engine:
    global _engine
    if _engine is None:
        _engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            pool_size=20,
            max_overflow=20,
            pool_timeout=10,
        )
    return _engine


class _LazyEngine:
    __func__ = None

    def __getattr__(self, name: str):
        return getattr(_get_engine(), name)


engine = _LazyEngine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=True)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
