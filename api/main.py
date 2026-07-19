from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

if __package__ in (None, ""):
    repo_root = str(Path(__file__).resolve().parent.parent)
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)

from api.app.core.config import BOT_TOKEN, CORS_ORIGINS, validate_config
from api.app.core.notification_worker import NotificationWorker
from api.app.db.seed import seed_reference_data
from api.app.routes.telegram_webhook import router as telegram_webhook_router
from api.app.routes.zoopark_core import router as core_router
from api.app.routes.zoopark_development import router as development_router
from api.app.routes.zoopark_admin import router as admin_router
from api.app.routes.zoopark_economy import router as economy_router
from api.app.routes.zoopark_forge import router as forge_router
from api.app.routes.zoopark_games import router as games_router
from api.app.routes.zoopark_merchant import router as merchant_router
from api.app.routes.zoopark_progression import router as progression_router
from api.app.routes.zoopark_social import router as social_router
from api.app.routes.zoopark_status import router as status_router
from api.app.routes.zoopark_subscriptions import router as subscriptions_router


def _configure_common_middleware(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=CORS_ORIGINS,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-Init-Data", "X-Dev-User-Id"],
    )


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Refuse to serve with an insecure configuration rather than degrading silently.
    validate_config()
    # The schema is Alembic's job alone; this only fills the reference tables.
    seed_reference_data()
    worker = NotificationWorker() if BOT_TOKEN else None
    if worker is not None:
        worker.start()
    try:
        yield
    finally:
        if worker is not None:
            worker.stop()


def create_app() -> FastAPI:
    app = FastAPI(title="ZooPark API", version="4.0.0", lifespan=lifespan)
    _configure_common_middleware(app)
    for router in (
        admin_router,
        core_router,
        development_router,
        economy_router,
        status_router,
        merchant_router,
        forge_router,
        social_router,
        subscriptions_router,
        games_router,
        progression_router,
        telegram_webhook_router,
    ):
        app.include_router(router)
    return app


app = create_app()
