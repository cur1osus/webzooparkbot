from api.app.db.models import Base

__all__ = ["Base", "SessionLocal", "engine", "get_session"]


def __getattr__(name: str):
    if name in {"SessionLocal", "engine", "get_session"}:
        from api.app.db import connection

        return getattr(connection, name)
    raise AttributeError(name)
