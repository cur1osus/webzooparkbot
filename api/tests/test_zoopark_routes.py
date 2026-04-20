from __future__ import annotations

import importlib
import inspect
import sys
import types
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from api.app.zoopark.db_tables import ZOOPARK_EXTRA_TABLE, ZOOPARK_USERS_TABLE


class _FakeRouter:
    def __init__(self, *args, **kwargs):
        self.routes = []

    def add_api_route(self, path: str, endpoint, methods=None, **_kwargs):
        self.routes.append((path, methods or [], endpoint))

    def get(self, path: str, **kwargs):
        return self._decorator(path, ["GET"], kwargs)

    def post(self, path: str, **kwargs):
        return self._decorator(path, ["POST"], kwargs)

    def _decorator(self, path: str, methods: list[str], kwargs: dict):
        def wrap(fn):
            self.add_api_route(path, fn, methods, **kwargs)
            return fn
        return wrap


class _FakeHTTPException(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class _FakeBaseModel:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


def _fake_field(*, alias=None, default=None, **_kwargs):
    return default


class _FakeRequest:
    async def json(self):
        return {}


class ZooParkRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self._saved_modules = dict(sys.modules)

        fastapi = types.ModuleType("fastapi")
        fastapi.APIRouter = _FakeRouter
        fastapi.Header = lambda default="": default
        fastapi.HTTPException = _FakeHTTPException
        fastapi.Request = _FakeRequest
        sys.modules["fastapi"] = fastapi

        pydantic = types.ModuleType("pydantic")
        pydantic.BaseModel = _FakeBaseModel
        pydantic.Field = _fake_field
        sys.modules["pydantic"] = pydantic

        pymysql = types.ModuleType("pymysql")
        pymysql.connect = lambda **_kwargs: None
        sys.modules["pymysql"] = pymysql

        pymysql_cursors = types.ModuleType("pymysql.cursors")
        pymysql_cursors.DictCursor = object
        sys.modules["pymysql.cursors"] = pymysql_cursors
        pymysql.cursors = pymysql_cursors

        for name in [
            "api.app.api.routes.zoopark_core",
            "api.app.api.routes.zoopark_economy",
            "api.app.api.routes.zoopark_status",
            "api.app.api.routes.zoopark_merchant",
            "api.app.api.routes.zoopark_forge",
            "api.app.api.routes.zoopark_social",
            "api.app.api.routes.zoopark_games",
            "api.app.api.routes.zoopark_progression",
            "api.app.zoopark.runtime",
            "api.app.zoopark.profile",
            "api.app.zoopark.catalog",
            "api.app.zoopark.income",
            "api.app.zoopark.merchant",
            "api.app.zoopark.forge",
            "api.app.zoopark.social",
            "api.app.zoopark.games",
            "api.app.zoopark.progression",
        ]:
            sys.modules.pop(name, None)

    def tearDown(self) -> None:
        sys.modules.clear()
        sys.modules.update(self._saved_modules)

    def _fake_db(self):
        db = MagicMock()
        cur = MagicMock()
        db.cursor.return_value.__enter__.return_value = cur
        return db, cur

    def test_config_contract(self) -> None:
        module = importlib.import_module("api.app.api.routes.zoopark_core")
        with patch.object(module, "BOT_USERNAME", "ZooParkBot"):
            self.assertEqual(module.config(), {"bot_username": "ZooParkBot"})

    def test_me_contract(self) -> None:
        module = importlib.import_module("api.app.api.routes.zoopark_core")
        db, _cur = self._fake_db()
        user = {"id": 7}
        state = {"tg_id": 1, "nickname": "tester"}

        with patch.object(module, "auth", return_value=1), \
             patch.object(module, "get_db", return_value=db), \
             patch.object(module, "get_user", return_value=user), \
             patch.object(module, "sync_passive_balance", return_value=(user, 123, 17)), \
             patch.object(module, "build_state", return_value=state):
            self.assertEqual(module.me(), state)

    def test_register_contract(self) -> None:
        module = importlib.import_module("api.app.api.routes.zoopark_core")
        db, cur = self._fake_db()
        db2, _cur2 = self._fake_db()
        user = {"id": 8, "id_user": 99, "nickname": "neo", "date_reg": "2026-01-01", "rub": 0, "usd": 1, "paw_coins": 0, "bonus": 1}
        cur.fetchone.side_effect = [None, user]

        with patch.object(module, "auth", return_value=99), \
             patch.object(module, "get_db", side_effect=[db, db2]), \
             patch.object(module, "get_user", return_value=None), \
             patch.object(module, "build_state", return_value={"tg_id": 99}):
            result = module.register(module.RegisterBody(nickname="neo"))
        self.assertEqual(result, {"ok": True, "game_state": {"tg_id": 99}})

    def test_save_contract(self) -> None:
        module = importlib.import_module("api.app.api.routes.zoopark_core")
        db, cur = self._fake_db()
        cur.fetchone.side_effect = [None, None]
        user = {"id": 1, "rub": 10, "usd": 0, "paw_coins": 0, "balance_seq": 17}
        body = module.SavePayload(
            rub=10,
            usd=2,
            paw_coins=3,
            animals=[{"animal_id": "rabbit", "quantity": 1}],
            aviaries=[{"aviary_id": "small", "count": 1}],
            balance_seq=0,
            data_version=0,
        )
        with patch.object(module, "auth", return_value=1), \
             patch.object(module, "get_db", return_value=db), \
             patch.object(module, "get_user", return_value=user), \
             patch.object(module, "sync_passive_balance", return_value=(user, 0, 0)), \
             patch.object(module, "get_extra", return_value={"balance_seq": 0, "data_version": 0}):
            self.assertEqual(
                module.save(body),
                {"ok": True, "rub": 10, "usd": 2, "paw_coins": 3, "balance_seq": 17, "data_version": 0},
            )

        update_calls = [call.args for call in cur.execute.call_args_list if call.args and isinstance(call.args[0], str) and call.args[0].startswith(f"UPDATE {ZOOPARK_USERS_TABLE} SET")]
        self.assertIn((f"UPDATE {ZOOPARK_USERS_TABLE} SET usd=%s, paw_coins=%s WHERE id=%s", (2, 3, 1)), update_calls)

    def test_save_uses_pre_sync_balance_seq_for_non_rub_fields(self) -> None:
        module = importlib.import_module("api.app.api.routes.zoopark_core")
        income_module = importlib.import_module("api.app.zoopark.income")

        class _StatefulCursor:
            def __init__(self) -> None:
                self.extra = {
                    "user_id": 1,
                    "balance_seq": 5,
                    "data_version": 0,
                    "profile_emoji": None,
                    "last_income_at": datetime(2026, 1, 1, 0, 0, 0),
                }
                self.last_sql = ""
                self.calls: list[tuple[str, tuple]] = []

            def execute(self, sql: str, params: tuple) -> None:
                self.last_sql = sql
                self.calls.append((sql, params))
                if sql.startswith(f"UPDATE {ZOOPARK_EXTRA_TABLE} SET last_income_at=%s, balance_seq=%s WHERE user_id=%s"):
                    self.extra["last_income_at"] = params[0]
                    self.extra["balance_seq"] = params[1]

            def fetchone(self):
                if self.last_sql.startswith(f"SELECT * FROM {ZOOPARK_EXTRA_TABLE} WHERE user_id=%s"):
                    return dict(self.extra)
                if self.last_sql.startswith(f"SELECT last_income_at, balance_seq FROM {ZOOPARK_EXTRA_TABLE} WHERE user_id=%s"):
                    return {
                        "last_income_at": self.extra["last_income_at"],
                        "balance_seq": self.extra["balance_seq"],
                    }
                return None

        class _StatefulDb:
            def __init__(self, cursor: _StatefulCursor) -> None:
                self._cursor = cursor

            def cursor(self):
                return self

            def __enter__(self):
                return self._cursor

            def __exit__(self, exc_type, exc, tb):
                return False

            def commit(self) -> None:
                return None

            def close(self) -> None:
                return None

        cur = _StatefulCursor()
        db = _StatefulDb(cur)
        user = {"id": 1, "rub": 10, "usd": 0, "paw_coins": 0}
        body = module.SavePayload(
            rub=10,
            usd=2,
            paw_coins=3,
            animals=[],
            aviaries=[],
            balance_seq=5,
            data_version=0,
        )

        with patch.object(module, "auth", return_value=1), \
             patch.object(module, "get_db", return_value=db), \
             patch.object(module, "get_user", return_value=user), \
             patch.object(income_module, "calc_pack_income", return_value=0), \
             patch.object(income_module, "calc_sick_expenses", return_value=0):
            result = module.save(body)

        self.assertGreater(cur.extra["balance_seq"], 5)
        self.assertEqual(result["rub"], 10)
        self.assertEqual(result["usd"], 2)
        self.assertEqual(result["paw_coins"], 3)
        self.assertEqual(result["balance_seq"], cur.extra["balance_seq"])
        self.assertIn((f"UPDATE {ZOOPARK_USERS_TABLE} SET usd=%s, paw_coins=%s WHERE id=%s", (2, 3, 1)), cur.calls)

    def test_bank_contract(self) -> None:
        module = importlib.import_module("api.app.api.routes.zoopark_economy")
        with patch.object(module, "auth", return_value=1):
            result = module.bank()
        self.assertEqual(result["rub_rate"], 90)
        self.assertIn("usd_rate", result)

    def test_bank_exchange_keeps_legacy_from_field_contract(self) -> None:
        module = importlib.import_module("api.app.api.routes.zoopark_economy")
        source = inspect.getsource(module.BankExchangeBody)
        self.assertIn('alias="from"', source)

        db, _cur = self._fake_db()
        user = {"id": 1, "rub": 500, "usd": 1}
        body = types.SimpleNamespace(from_="rub", amount=180)
        with patch.object(module, "auth", return_value=1), \
             patch.object(module, "get_db", return_value=db), \
             patch.object(module, "get_user", return_value=user), \
             patch.object(module, "sync_passive_balance", return_value=(user, 0, 0)):
            result = module.bank_exchange(body)
        self.assertEqual(result, {"ok": True, "new_rub": 320, "new_usd": 3})

    def test_claim_bonus_contract(self) -> None:
        module = importlib.import_module("api.app.api.routes.zoopark_status")
        db, _cur = self._fake_db()
        user = {"id": 1, "bonus": 1, "rub": 100, "usd": 2, "paw_coins": 3}
        with patch.object(module, "auth", return_value=1), \
             patch.object(module, "get_db", return_value=db), \
             patch.object(module, "get_user", return_value=user), \
             patch.object(module, "sync_passive_balance", return_value=(user, 0, 0)), \
             patch.object(module.random, "choice", return_value="rub"), \
             patch.object(module.random, "randint", return_value=500):
            result = module.claim_bonus()
        self.assertEqual(result, {"ok": True, "type": "rub", "amount": 500, "new_rub": 600, "message": "Получено 500 ₽"})

    def test_cure_animal_contract(self) -> None:
        module = importlib.import_module("api.app.api.routes.zoopark_status")
        db, cur = self._fake_db()
        cur.fetchone.side_effect = [{"id": 1}]
        user = {"id": 1, "paw_coins": 30}
        body = module.CureBody(animal_id="rabbit")
        with patch.object(module, "auth", return_value=1), \
             patch.object(module, "get_db", return_value=db), \
             patch.object(module, "get_user", return_value=user):
            result = module.cure_animal(body)
        self.assertEqual(result, {"ok": True, "cost_paw_coins": 10, "new_paw_coins": 20})

    def test_merchant_route_inventory(self) -> None:
        module = importlib.import_module("api.app.api.routes.zoopark_merchant")
        route_paths = {path for path, _methods, _endpoint in module.router.routes}
        self.assertEqual(route_paths, {
            "/api/merchant/animals",
            "/api/merchant/buy1",
            "/api/merchant/buy2",
            "/api/merchant/buy3",
        })
        self.assertNotIn("delegates", inspect.getsource(module))

    def test_forge_route_inventory(self) -> None:
        module = importlib.import_module("api.app.api.routes.zoopark_forge")
        route_paths = {path for path, _methods, _endpoint in module.router.routes}
        self.assertEqual(route_paths, {
            "/api/forge/items",
            "/api/forge/create",
            "/api/forge/upgrade",
            "/api/forge/merge",
            "/api/forge/sell",
            "/api/forge/activate",
        })
        self.assertNotIn("delegates", inspect.getsource(module))

    def test_social_route_inventory(self) -> None:
        module = importlib.import_module("api.app.api.routes.zoopark_social")
        route_paths = {path for path, _methods, _endpoint in module.router.routes}
        self.assertIn("/api/top", route_paths)
        self.assertIn("/api/clan/list", route_paths)
        self.assertIn("/api/referrals", route_paths)
        self.assertIn("/api/transfers/create", route_paths)
        self.assertIn("/api/my-transfers", route_paths)
        self.assertNotIn("delegates", inspect.getsource(module))

    def test_games_route_inventory(self) -> None:
        module = importlib.import_module("api.app.api.routes.zoopark_games")
        route_paths = {path for path, _methods, _endpoint in module.router.routes}
        self.assertIn("/api/mpgame/open", route_paths)
        self.assertIn("/api/start_solo_game", route_paths)
        self.assertIn("/api/get_solo_stats", route_paths)
        self.assertIn("/api/donate/info", route_paths)
        self.assertIn("/api/cocktail/guess", route_paths)
        self.assertNotIn("delegates", inspect.getsource(module))

    def test_progression_route_inventory(self) -> None:
        module = importlib.import_module("api.app.api.routes.zoopark_progression")
        route_paths = {path for path, _methods, _endpoint in module.router.routes}
        self.assertIn("/api/packs/info", route_paths)
        self.assertIn("/api/localities", route_paths)
        self.assertIn("/api/breed", route_paths)
        self.assertIn("/api/expeditions", route_paths)
        self.assertIn("/api/expeditions/finish", route_paths)
        self.assertNotIn("delegates", inspect.getsource(module))

    def test_donate_info_contract(self) -> None:
        module = importlib.import_module("api.app.zoopark.games")
        self.assertEqual(module.api_donate_info(), {"stars_to_paw": 10})

    def test_buy_locality_contract(self) -> None:
        module = importlib.import_module("api.app.zoopark.progression")
        db, cur = self._fake_db()
        cur.lastrowid = 1
        user = {"id": 1, "rub": 120000}
        cur.fetchone.side_effect = [
            {"cnt": 1, "taken": "forest"},
        ]
        with patch.object(module, "get_db", return_value=db), \
             patch.object(module, "get_user", return_value=user), \
             patch.object(module, "sync_passive_balance", return_value=(user, 0, 0)):
            result = module.api_buy_locality(1, module.BuyLocalityBody(habitat="desert"))
        self.assertEqual(result, {"ok": True, "id": 1, "habitat": "desert", "price_paid": 50000, "new_rub": 70000})

    def test_merchant_animals_contract(self) -> None:
        module = importlib.import_module("api.app.zoopark.merchant")
        db, _cur = self._fake_db()
        offers = [{"animal_info_id": 1, "quantity_animals": 2, "price": 1100, "discount": 10, "price_with_discount": 990}]
        with patch.object(module, "get_db", return_value=db), \
             patch.object(module, "get_user", return_value={"id": 7}), \
             patch.object(module, "get_animals", return_value=[]), \
             patch.object(module, "ensure_merchant", return_value=offers):
            result = module.get_merchant_animals(1)
        self.assertEqual(result["animals"], [{"slot": 1, "animal_id": "rabbit", "quantity": 2, "original_price": 1100, "discount_pct": 10, "final_price": 990}])

    def test_merchant_buy_uses_bundle_quantity_for_total_cost(self) -> None:
        module = importlib.import_module("api.app.zoopark.merchant")
        db, cur = self._fake_db()
        user = {"id": 7, "rub": 5000}
        offer = {"animal_info_id": 1, "quantity_animals": 3, "price_with_discount": 990, "first_offer_bought": 0}
        with patch.object(module, "get_db", return_value=db), \
             patch.object(module, "get_user", return_value=user), \
             patch.object(module, "get_animals", return_value=[]), \
             patch.object(module, "get_aviaries", return_value=[{"aviary_id": "small", "count": 1}]), \
             patch.object(module, "ensure_merchant", return_value=[offer]), \
             patch.object(module, "bump_data_version"):
            cur.fetchone.return_value = None
            result = module.buy_merchant_offer(1, 1)
        self.assertEqual(result, {"ok": True, "new_rub": 2030, "new_quantity": 3})

    def test_forge_create_contract(self) -> None:
        module = importlib.import_module("api.app.zoopark.forge")
        db, cur = self._fake_db()
        cur.lastrowid = 42
        cur.fetchone.return_value = {"cnt": 0}
        with patch.object(module, "get_db", return_value=db), \
             patch.object(module, "get_user", return_value={"id": 9, "paw_coins": 500, "usd": 1000}), \
             patch.object(module, "_make_properties", return_value=[{"type": "income_boost", "value": 7, "label": "Общий доход +7"}]), \
             patch.object(module.random, "choices", return_value=["rare"]):
            result = module.api_forge_create(1, module.ForgeCreateBody(currency="paw"))
        self.assertEqual(result["item"]["id"], "42")
        self.assertEqual(result["item"]["rarity"], "rare")
        self.assertEqual(result["new_paw_coins"], 150)

    def test_top_contract(self) -> None:
        module = importlib.import_module("api.app.zoopark.social")
        db, cur = self._fake_db()
        cur.fetchall.return_value = [{"id": 1, "id_user": 77, "nickname": "neo", "income": 1234}]
        cur.fetchone.return_value = {"id": 1}
        with patch.object(module, "get_db", return_value=db):
            result = module.api_top(77)
        self.assertEqual(result, {"entries": [{"rank": 1, "tg_id": 77, "nickname": "neo", "income_rub_per_min": 1234, "name_color": None, "is_me": True}], "my_rank": 1})

    def test_clan_request_joins_immediately(self) -> None:
        module = importlib.import_module("api.app.zoopark.social")
        db, cur = self._fake_db()
        cur.fetchone.side_effect = [{"idpk": 22, "name": "Wolves"}]
        with patch.object(module, "get_db", return_value=db), \
             patch.object(module, "get_user", return_value={"id": 15, "unity_id": None}):
            result = module.api_clan_request(77, module.ClanRequestBody(clan_id=22))
        self.assertEqual(result, {"ok": True, "message": "Вступил в клан «Wolves»"})

    def test_mpgame_join_resolves_game_immediately(self) -> None:
        module = importlib.import_module("api.app.zoopark.games")
        db, cur = self._fake_db()
        cur.fetchone.side_effect = [
            {"id": 5, "status": "open", "creator_id": 1, "bet_rub": 100, "game_type": "dice", "created_at": "2026-01-01T00:00:00+00:00"},
            {"nickname": "host"},
            {"nickname": "host"},
        ]
        with patch.object(module, "get_db", return_value=db), \
             patch.object(module, "get_user", return_value={"id": 9, "rub": 500, "nickname": "guest"}), \
             patch.object(module, "sync_passive_balance", return_value=({"id": 9, "rub": 500, "nickname": "guest"}, 0, 0)), \
             patch.object(module.random, "randint", side_effect=[6, 2]):
            result = module.api_mpgame_join(77, 5)
        self.assertEqual(result["game"]["status"], "finished")
        self.assertEqual(result["game"]["winner_nickname"], "host")

    def test_start_solo_basketball_returns_history_and_refunds_draw(self) -> None:
        module = importlib.import_module("api.app.zoopark.games")
        db, cur = self._fake_db()

        with patch.object(module, "get_db", return_value=db), \
             patch.object(module, "get_user", return_value={"id": 11, "rub": 1000, "nickname": "neo"}), \
             patch.object(module, "sync_passive_balance", return_value=({"id": 11, "rub": 1000, "nickname": "neo"}, 0, 0)), \
             patch.object(module.random, "randint", side_effect=[5, 5, 0, 0, 4, 4, 1, 1, 3, 3]):
            result = module.api_start_solo_game(77, module.SoloStartBody(game_type="basketball", bet_rub=100))

        self.assertTrue(result["ok"])
        self.assertEqual(result["result"], "Счёт: 6 — 6")
        self.assertEqual(result["rub_delta"], 0)
        self.assertTrue(result["is_draw"])
        self.assertEqual(len(result["history"]), 5)
        self.assertEqual(result["history"][0], {"round": 1, "player_roll": 5, "ai_roll": 5})

    def test_get_expeditions_auto_resolves_expired_active_expedition(self) -> None:
        module = importlib.import_module("api.app.zoopark.progression")
        db, cur = self._fake_db()
        past = datetime(2020, 1, 1, 0, 0, 0)
        cur.fetchall.side_effect = [
            [{"id": 1, "habitat": "forest"}],
            [],
            [],
        ]
        cur.fetchone.side_effect = [
            {"id": 99, "status": "active", "locality_habitat": "forest", "started_at": "2026-01-01T00:00:00+00:00", "ends_at": past, "result_json": None},
        ]
        with patch.object(module, "get_db", return_value=db), \
             patch.object(module, "get_user", return_value={"id": 8}), \
             patch.object(module, "resolve_expedition", return_value={"outcome": "victory", "reward_animal_id": None}), \
             patch.object(module, "format_pack_animal", side_effect=lambda animal: animal):
            result = module.api_get_expeditions(77)
        self.assertEqual(result["active"]["status"], "finished")
        self.assertEqual(result["active"]["result"], {"outcome": "victory", "reward_animal_id": None})


if __name__ == "__main__":
    unittest.main()
