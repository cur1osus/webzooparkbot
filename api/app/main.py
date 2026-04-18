from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.app.api.routes.zoopark_forge import router as zoopark_forge_router
from api.app.api.routes.zoopark_games import router as zoopark_games_router
from api.app.api.routes.zoopark_economy import router as zoopark_economy_router
from api.app.api.routes.zoopark_core import router as zoopark_core_router
from api.app.api.routes.zoopark_merchant import router as zoopark_merchant_router
from api.app.api.routes.zoopark_progression import router as zoopark_progression_router
from api.app.api.routes.zoopark_social import router as zoopark_social_router
from api.app.api.routes.zoopark_status import router as zoopark_status_router
from api.app.zoopark.bootstrap import init_schema


def _configure_common_middleware(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

def _init_legacy_schema() -> None:
    init_schema()


@asynccontextmanager
async def lifespan(_: FastAPI):
    _init_legacy_schema()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="ZooPark API", version="3.0.0", lifespan=lifespan)
    _configure_common_middleware(app)
    app.include_router(zoopark_core_router)
    app.include_router(zoopark_economy_router)
    app.include_router(zoopark_status_router)
    app.include_router(zoopark_merchant_router)
    app.include_router(zoopark_forge_router)
    app.include_router(zoopark_social_router)
    app.include_router(zoopark_games_router)
    app.include_router(zoopark_progression_router)
    return app


app = create_app()
