from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.app.api.routes.game import router as game_router
from api.app.api.routes.zoopark_forge import router as zoopark_forge_router
from api.app.api.routes.zoopark_games import router as zoopark_games_router
from api.app.api.routes.zoopark_economy import router as zoopark_economy_router
from api.app.api.routes.more import router as more_router
from api.app.api.routes.zoopark_core import router as zoopark_core_router
from api.app.api.routes.zoopark_merchant import router as zoopark_merchant_router
from api.app.api.routes.zoopark_progression import router as zoopark_progression_router
from api.app.api.routes.zoopark_social import router as zoopark_social_router
from api.app.api.routes.zoopark_status import router as zoopark_status_router
from api.app.core.errors import AppError
from api.app.zoopark.bootstrap import init_schema


def _configure_common_middleware(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )


def create_native_app() -> FastAPI:
    app = FastAPI(title="Merchant's Menagerie API", version="1.0.0")

    @app.exception_handler(AppError)
    async def handle_app_error(_, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    _configure_common_middleware(app)
    app.include_router(game_router)
    app.include_router(more_router)
    return app


def _init_legacy_schema() -> None:
    init_schema()


@asynccontextmanager
async def lifespan(_: FastAPI):
    _init_legacy_schema()
    yield


def create_app() -> FastAPI:
    app = FastAPI(title="ZooPark API Gateway", version="2.0.0", lifespan=lifespan)
    _configure_common_middleware(app)
    app.include_router(zoopark_core_router)
    app.include_router(zoopark_economy_router)
    app.include_router(zoopark_status_router)
    app.include_router(zoopark_merchant_router)
    app.include_router(zoopark_forge_router)
    app.include_router(zoopark_social_router)
    app.include_router(zoopark_games_router)
    app.include_router(zoopark_progression_router)
    app.mount("/v2", create_native_app())
    return app


app = create_app()
