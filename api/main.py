from __future__ import annotations

try:
    from api.app.main import create_app
except ModuleNotFoundError as exc:
    if exc.name != "api":
        raise
    # Compatibility for deployments that still boot `uvicorn main:app`
    # from inside `/api` instead of the repository root.
    from app.main import create_app


app = create_app()
legacy_app = app
