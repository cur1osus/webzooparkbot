from __future__ import annotations

import importlib
import inspect
import sys
import types
import unittest
from pathlib import Path


class _FakeRouter:
    def __init__(self, *, prefix: str = "", tags: list[str] | None = None):
        self.prefix = prefix
        self.tags = tags or []
        self.routes: list[dict[str, object]] = []

    def add_api_route(self, path: str, endpoint, methods: list[str] | None = None, **_kwargs) -> None:
        self.routes.append({"path": path, "methods": methods or [], "endpoint": endpoint})

    def get(self, path: str, **kwargs):
        return self._decorator(["GET"], path, kwargs)

    def post(self, path: str, **kwargs):
        return self._decorator(["POST"], path, kwargs)

    def _decorator(self, methods: list[str], path: str, kwargs: dict[str, object]):
        def decorate(fn):
            self.add_api_route(f"{self.prefix}{path}", fn, methods=methods, **kwargs)
            return fn
        return decorate


class _FakeFastAPI:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.routes: list[types.SimpleNamespace] = []
        self.user_middleware: list[object] = []

    def add_middleware(self, middleware_cls, **kwargs) -> None:
        self.user_middleware.append((middleware_cls, kwargs))

    def include_router(self, router: _FakeRouter) -> None:
        for route in router.routes:
            self.routes.append(types.SimpleNamespace(path=route["path"], methods=route["methods"], endpoint=route["endpoint"]))

    def mount(self, path: str, app) -> None:
        self.routes.append(types.SimpleNamespace(path=path, methods=[], app=app))

    def exception_handler(self, _exc_cls):
        def decorate(fn):
            return fn
        return decorate
class ApiGatewayTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved_modules = dict(sys.modules)

        fastapi = types.ModuleType("fastapi")
        fastapi.FastAPI = _FakeFastAPI
        fastapi.APIRouter = _FakeRouter
        fastapi.HTTPException = type("HTTPException", (Exception,), {})
        sys.modules["fastapi"] = fastapi

        cors = types.ModuleType("fastapi.middleware.cors")
        cors.CORSMiddleware = object
        sys.modules["fastapi.middleware.cors"] = cors

        pymysql = types.ModuleType("pymysql")
        pymysql.connect = lambda **_kwargs: None
        sys.modules["pymysql"] = pymysql

        pymysql_cursors = types.ModuleType("pymysql.cursors")
        pymysql_cursors.DictCursor = object
        sys.modules["pymysql.cursors"] = pymysql_cursors
        pymysql.cursors = pymysql_cursors

        zoopark_core_routes = types.ModuleType("api.app.api.routes.zoopark_core")
        zoopark_core_router = _FakeRouter(tags=["zoopark-core"])
        zoopark_core_router.add_api_route("/api/health", lambda: None, methods=["GET"])
        zoopark_core_router.add_api_route("/api/me", lambda: None, methods=["GET"])
        zoopark_core_router.add_api_route("/api/save", lambda: None, methods=["POST"])
        zoopark_core_router.add_api_route("/api/register", lambda: None, methods=["POST"])
        zoopark_core_router.add_api_route("/api/config", lambda: None, methods=["GET"])
        zoopark_core_routes.router = zoopark_core_router
        sys.modules["api.app.api.routes.zoopark_core"] = zoopark_core_routes

        zoopark_economy_routes = types.ModuleType("api.app.api.routes.zoopark_economy")
        zoopark_economy_router = _FakeRouter(tags=["zoopark-economy"])
        zoopark_economy_router.add_api_route("/api/buy_animal", lambda: None, methods=["POST"])
        zoopark_economy_router.add_api_route("/api/buy_aviary", lambda: None, methods=["POST"])
        zoopark_economy_router.add_api_route("/api/bank", lambda: None, methods=["GET"])
        zoopark_economy_router.add_api_route("/api/bank/exchange", lambda: None, methods=["POST"])
        zoopark_economy_routes.router = zoopark_economy_router
        sys.modules["api.app.api.routes.zoopark_economy"] = zoopark_economy_routes

        zoopark_status_routes = types.ModuleType("api.app.api.routes.zoopark_status")
        zoopark_status_router = _FakeRouter(tags=["zoopark-status"])
        zoopark_status_router.add_api_route("/api/claim_bonus", lambda: None, methods=["POST"])
        zoopark_status_router.add_api_route("/api/cure_animal", lambda: None, methods=["POST"])
        zoopark_status_routes.router = zoopark_status_router
        sys.modules["api.app.api.routes.zoopark_status"] = zoopark_status_routes

        zoopark_merchant_routes = types.ModuleType("api.app.api.routes.zoopark_merchant")
        zoopark_merchant_router = _FakeRouter(tags=["zoopark-merchant"])
        zoopark_merchant_router.add_api_route("/api/merchant/animals", lambda: None, methods=["GET"])
        zoopark_merchant_routes.router = zoopark_merchant_router
        sys.modules["api.app.api.routes.zoopark_merchant"] = zoopark_merchant_routes

        zoopark_forge_routes = types.ModuleType("api.app.api.routes.zoopark_forge")
        zoopark_forge_router = _FakeRouter(tags=["zoopark-forge"])
        zoopark_forge_router.add_api_route("/api/forge/items", lambda: None, methods=["GET"])
        zoopark_forge_routes.router = zoopark_forge_router
        sys.modules["api.app.api.routes.zoopark_forge"] = zoopark_forge_routes

        zoopark_social_routes = types.ModuleType("api.app.api.routes.zoopark_social")
        zoopark_social_router = _FakeRouter(tags=["zoopark-social"])
        zoopark_social_router.add_api_route("/api/top", lambda: None, methods=["GET"])
        zoopark_social_router.add_api_route("/api/clan/list", lambda: None, methods=["GET"])
        zoopark_social_routes.router = zoopark_social_router
        sys.modules["api.app.api.routes.zoopark_social"] = zoopark_social_routes

        zoopark_games_routes = types.ModuleType("api.app.api.routes.zoopark_games")
        zoopark_games_router = _FakeRouter(tags=["zoopark-games"])
        zoopark_games_router.add_api_route("/api/mpgame/open", lambda: None, methods=["GET"])
        zoopark_games_router.add_api_route("/api/cocktail/guess", lambda: None, methods=["POST"])
        zoopark_games_routes.router = zoopark_games_router
        sys.modules["api.app.api.routes.zoopark_games"] = zoopark_games_routes

        zoopark_progression_routes = types.ModuleType("api.app.api.routes.zoopark_progression")
        zoopark_progression_router = _FakeRouter(tags=["zoopark-progression"])
        zoopark_progression_router.add_api_route("/api/packs/info", lambda: None, methods=["GET"])
        zoopark_progression_router.add_api_route("/api/expeditions/finish", lambda: None, methods=["POST"])
        zoopark_progression_routes.router = zoopark_progression_router
        sys.modules["api.app.api.routes.zoopark_progression"] = zoopark_progression_routes

        for name in [
            "api.app.main",
        ]:
            sys.modules.pop(name, None)

    def tearDown(self) -> None:
        sys.modules.clear()
        sys.modules.update(self._saved_modules)

    def test_runtime_combined_app_contains_primary_zoopark_routes(self) -> None:
        app_main = importlib.import_module("api.app.main")
        app = app_main.create_app()
        route_paths = {route.path for route in app.routes}

        self.assertIn("/api/health", route_paths)
        self.assertIn("/api/me", route_paths)
        self.assertIn("/api/save", route_paths)
        self.assertIn("/api/bank", route_paths)
        self.assertIn("/api/claim_bonus", route_paths)
        self.assertIn("/api/merchant/animals", route_paths)
        self.assertIn("/api/forge/items", route_paths)
        self.assertIn("/api/top", route_paths)
        self.assertIn("/api/mpgame/open", route_paths)
        self.assertIn("/api/expeditions/finish", route_paths)
        self.assertNotIn("/v2", route_paths)

    def test_combined_app_no_longer_uses_legacy_router_module(self) -> None:
        app_main_module = importlib.import_module("api.app.main")
        source = inspect.getsource(app_main_module)
        self.assertNotIn("legacy_router", source)

    def test_api_main_is_thin_canonical_shell(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        source = (repo_root / "api" / "main.py").read_text(encoding="utf-8")

        self.assertIn("create_app", source)
        self.assertNotIn("SourcelessFileLoader", source)
        self.assertNotIn("legacy_main", source)
        self.assertNotIn("legacy_app", source)
        self.assertNotIn("@app.get(", source)
        self.assertNotIn("@app.post(", source)
        self.assertFalse((repo_root / "api" / "app" / "zoopark" / "delegates.py").exists())


if __name__ == "__main__":
    unittest.main()
