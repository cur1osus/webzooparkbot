from __future__ import annotations

import importlib
import inspect
import sys
import types
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

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
            "api.app.routes.zoopark_core",
            "api.app.routes.zoopark_economy",
            "api.app.routes.zoopark_status",
            "api.app.routes.zoopark_merchant",
            "api.app.routes.zoopark_forge",
            "api.app.routes.zoopark_social",
            "api.app.routes.zoopark_games",
            "api.app.routes.zoopark_progression",
            "api.app.core.auth",
            "api.app.core.config",
            "api.app.db.connection",
            "api.app.zoopark.profile",
            "api.app.zoopark.catalog",
            "api.app.zoopark.income",
            "api.app.zoopark.core",
            "api.app.zoopark.economy",
            "api.app.zoopark.status",
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

    def _fake_session(self):
        session = MagicMock()
        ctx = MagicMock()
        ctx.__enter__.return_value = session
        ctx.__exit__.return_value = False
        return ctx, session

    def test_config_contract(self) -> None:
        module = importlib.import_module("api.app.zoopark.core")
        with patch.object(module, "BOT_USERNAME", "ZooParkBot"):
            self.assertEqual(module.config(), {"bot_username": "ZooParkBot"})

    def test_me_contract(self) -> None:
        module = importlib.import_module("api.app.zoopark.core")
        ctx, session = self._fake_session()
        user = SimpleNamespace(id=7)
        state = {"tg_id": 1, "nickname": "tester"}

        with patch.object(module, "get_session", return_value=ctx), \
             patch.object(module, "get_user", return_value=user), \
             patch.object(module, "sync_passive_balance", return_value=(user, 123, 17)), \
             patch.object(module, "build_state", return_value=state):
            self.assertEqual(module.me(1), state)
        session.commit.assert_called_once()

    def test_register_contract(self) -> None:
        module = importlib.import_module("api.app.zoopark.core")
        ctx, session = self._fake_session()
        session.query.return_value.filter.return_value.first.return_value = None

        with patch.object(module, "get_session", return_value=ctx), \
             patch.object(module, "get_user", return_value=None), \
             patch.object(module, "build_state", return_value={"tg_id": 99}):
            result = module.register(99, module.RegisterBody(nickname="neo"))
        self.assertEqual(result, {"ok": True, "game_state": {"tg_id": 99}})
        session.add.assert_called()
        session.commit.assert_called_once()

    def test_save_contract(self) -> None:
        module = importlib.import_module("api.app.zoopark.core")
        ctx, session = self._fake_session()
        session.query.return_value.filter_by.return_value.first.return_value = None
        user = SimpleNamespace(id=1, rub=10, usd=0, paw_coins=0, balance_seq=17, data_version=0)
        body = module.SavePayload(
            rub=10,
            usd=2,
            paw_coins=3,
            animals=[{"animal_id": "rabbit", "quantity": 1}],
            aviaries=[{"aviary_id": "small", "count": 1}],
            balance_seq=17,
            data_version=0,
        )
        with patch.object(module, "get_session", return_value=ctx), \
             patch.object(module, "get_user", return_value=user), \
             patch.object(module, "sync_passive_balance", return_value=(user, 0, 0)):
            self.assertEqual(
                module.save(1, body),
                {"ok": True, "rub": 10, "usd": 2, "paw_coins": 3, "balance_seq": 17, "data_version": 0},
            )

        self.assertEqual(user.usd, 2)
        self.assertEqual(user.paw_coins, 3)
        session.add.assert_not_called()

    def test_save_uses_pre_sync_balance_seq_for_non_rub_fields(self) -> None:
        module = importlib.import_module("api.app.zoopark.core")
        ctx, session = self._fake_session()
        session.query.return_value.filter_by.return_value.first.return_value = None
        user = SimpleNamespace(id=1, rub=10, usd=0, paw_coins=0, balance_seq=5, data_version=0)
        body = module.SavePayload(
            rub=10,
            usd=2,
            paw_coins=3,
            animals=[],
            aviaries=[],
            balance_seq=5,
            data_version=0,
        )

        def _sync(_session, synced_user):
            synced_user.balance_seq = 6
            return synced_user, 0, 0

        with patch.object(module, "get_session", return_value=ctx), \
             patch.object(module, "get_user", return_value=user), \
             patch.object(module, "sync_passive_balance", side_effect=_sync):
            result = module.save(1, body)

        self.assertGreater(user.balance_seq, 5)
        self.assertEqual(result["rub"], 10)
        self.assertEqual(result["usd"], 2)
        self.assertEqual(result["paw_coins"], 3)
        self.assertEqual(result["balance_seq"], user.balance_seq)
        self.assertEqual(user.usd, 2)
        self.assertEqual(user.paw_coins, 3)

    def test_bank_contract(self) -> None:
        module = importlib.import_module("api.app.zoopark.economy")
        result = module.bank()
        self.assertEqual(result["rub_rate"], 90)
        self.assertIn("usd_rate", result)

    def test_bank_exchange_keeps_legacy_from_field_contract(self) -> None:
        module = importlib.import_module("api.app.zoopark.economy")
        source = inspect.getsource(module.BankExchangeBody)
        self.assertIn('alias="from"', source)

        ctx, session = self._fake_session()
        user = SimpleNamespace(id=1, rub=500, usd=1)
        body = types.SimpleNamespace(from_="rub", amount=180)
        with patch.object(module, "get_session", return_value=ctx), \
             patch.object(module, "get_user", return_value=user), \
             patch.object(module, "sync_passive_balance", return_value=(user, 0, 0)):
            result = module.bank_exchange(1, body)
        self.assertEqual(result, {"ok": True, "new_rub": 320, "new_usd": 3})
        session.commit.assert_called_once()

    def test_claim_bonus_contract(self) -> None:
        module = importlib.import_module("api.app.zoopark.status")
        ctx, _session = self._fake_session()
        user = SimpleNamespace(id=1, bonus=1, rub=100, usd=2, paw_coins=3)
        with patch.object(module, "get_session", return_value=ctx), \
             patch.object(module, "get_user", return_value=user), \
             patch.object(module, "sync_passive_balance", return_value=(user, 0, 0)), \
             patch.object(module.random, "choice", return_value="rub"), \
             patch.object(module.random, "randint", return_value=500):
            result = module.claim_bonus(1)
        self.assertEqual(result, {"ok": True, "type": "rub", "amount": 500, "new_rub": 600, "message": "Получено 500 ₽"})

    def test_cure_animal_contract(self) -> None:
        module = importlib.import_module("api.app.zoopark.status")
        ctx, session = self._fake_session()
        session.query.return_value.filter_by.return_value.first.return_value = SimpleNamespace(id=1)
        user = SimpleNamespace(id=1, paw_coins=30)
        body = module.CureBody(animal_id="1")
        with patch.object(module, "get_session", return_value=ctx), \
             patch.object(module, "get_user", return_value=user):
            result = module.cure_animal(1, body)
        self.assertEqual(result, {"ok": True, "cost_paw_coins": 10, "new_paw_coins": 20})
        session.delete.assert_called_once()

    def test_merchant_route_inventory(self) -> None:
        module = importlib.import_module("api.app.routes.zoopark_merchant")
        route_paths = {path for path, _methods, _endpoint in module.router.routes}
        self.assertEqual(route_paths, {
            "/api/merchant/animals",
            "/api/merchant/buy1",
            "/api/merchant/buy2",
            "/api/merchant/buy3",
        })
        self.assertNotIn("delegates", inspect.getsource(module))

    def test_forge_route_inventory(self) -> None:
        module = importlib.import_module("api.app.routes.zoopark_forge")
        route_paths = {path for path, _methods, _endpoint in module.router.routes}
        self.assertEqual(route_paths, {
            "/api/forge/items",
            "/api/forge/sets",
            "/api/forge/create",
            "/api/forge/sets/create",
            "/api/forge/sets/update",
            "/api/forge/sets/delete",
            "/api/forge/sets/apply",
            "/api/forge/upgrade",
            "/api/forge/merge",
            "/api/forge/sell",
            "/api/forge/activate",
        })
        self.assertNotIn("delegates", inspect.getsource(module))

    def test_social_route_inventory(self) -> None:
        module = importlib.import_module("api.app.routes.zoopark_social")
        route_paths = {path for path, _methods, _endpoint in module.router.routes}
        self.assertIn("/api/top", route_paths)
        self.assertIn("/api/clan/list", route_paths)
        self.assertIn("/api/referrals", route_paths)
        self.assertIn("/api/transfers/create", route_paths)
        self.assertIn("/api/my-transfers", route_paths)
        self.assertNotIn("delegates", inspect.getsource(module))

    def test_games_route_inventory(self) -> None:
        module = importlib.import_module("api.app.routes.zoopark_games")
        route_paths = {path for path, _methods, _endpoint in module.router.routes}
        self.assertIn("/api/mpgame/open", route_paths)
        self.assertIn("/api/start_solo_game", route_paths)
        self.assertIn("/api/get_solo_stats", route_paths)
        self.assertIn("/api/donate/info", route_paths)
        self.assertIn("/api/cocktail/guess", route_paths)
        self.assertNotIn("delegates", inspect.getsource(module))

    def test_progression_route_inventory(self) -> None:
        module = importlib.import_module("api.app.routes.zoopark_progression")
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
        ctx, session = self._fake_session()
        user = SimpleNamespace(id=1, rub=120000)
        session.query.return_value.filter.return_value.all.return_value = [SimpleNamespace(habitat="forest")]
        session.add.side_effect = lambda obj: setattr(obj, "id", 1)
        with patch.object(module, "get_session", return_value=ctx), \
             patch.object(module, "get_user", return_value=user), \
             patch.object(module, "sync_passive_balance", return_value=(user, 0, 0)):
            result = module.api_buy_locality(1, module.BuyLocalityBody(habitat="desert"))
        self.assertEqual(result, {"ok": True, "id": 1, "habitat": "desert", "price_paid": 50000, "new_rub": 70000})

    def test_merchant_animals_contract(self) -> None:
        module = importlib.import_module("api.app.zoopark.merchant")
        ctx, session = self._fake_session()
        offers = [SimpleNamespace(
            animal_info_id=1, price=1100, discount=10, price_with_discount=990,
            survival="low", reproduction="medium", appearance="high", size_trait="medium",
            habitat="fields", bought=0, expires_at=datetime(2026, 1, 1, 0, 0, 0),
        )]
        with patch.object(module, "get_session", return_value=ctx), \
             patch.object(module, "get_user", return_value=SimpleNamespace(id=7)), \
             patch.object(module, "ensure_player_season", return_value=SimpleNamespace(id=3)), \
             patch.object(module, "ensure_merchant", return_value=offers):
            result = module.get_merchant_animals(1)
        self.assertEqual(result["animals"][0]["animal_id"], "rabbit")
        self.assertEqual(result["animals"][0]["quantity"], 1)
        self.assertEqual(result["animals"][0]["final_price"], 990)
        self.assertEqual(result["animals"][0]["survival"], "low")

    def test_merchant_buy_creates_pack_animal(self) -> None:
        module = importlib.import_module("api.app.zoopark.merchant")
        ctx, session = self._fake_session()
        session.query.return_value.filter_by.return_value.first.return_value = None
        user = SimpleNamespace(id=7, rub=5000)
        offer = SimpleNamespace(
            animal_info_id=1, price_with_discount=990, bought=0,
            survival="low", reproduction="medium", appearance="high", size_trait="medium", habitat="fields",
        )
        session.add.side_effect = lambda obj: setattr(obj, "id", 55)
        with patch.object(module, "get_session", return_value=ctx), \
             patch.object(module, "get_user", return_value=user), \
             patch.object(module, "ensure_player_season", return_value=SimpleNamespace(id=3)), \
             patch.object(module, "ensure_merchant", return_value=[offer]), \
             patch.object(module, "sync_passive_balance", return_value=(user, 0, 0)), \
             patch.object(module, "bump_data_version"):
            result = module.buy_merchant_offer(1, 1)
        self.assertEqual(result["ok"], True)
        self.assertEqual(result["new_rub"], 4010)
        self.assertEqual(result["animal"]["source"], "merchant")

    def test_forge_create_contract(self) -> None:
        module = importlib.import_module("api.app.zoopark.forge")
        ctx, session = self._fake_session()
        session.query.return_value.filter.return_value.count.return_value = 0
        session.add.side_effect = lambda obj: setattr(obj, "id", 42)
        with patch.object(module, "get_session", return_value=ctx), \
             patch.object(module, "get_user", return_value=SimpleNamespace(id=9, paw_coins=500, usd=1000)), \
             patch.object(module, "_make_properties", return_value=[{"type": "income_boost", "value": 7, "label": "Общий доход +7"}]), \
             patch.object(module.random, "choices", return_value=["rare"]):
            result = module.api_forge_create(1, module.ForgeCreateBody(currency="paw"))
        self.assertEqual(result["item"]["id"], "42")
        self.assertEqual(result["item"]["rarity"], "rare")
        self.assertEqual(result["new_paw_coins"], 150)

    def test_forge_set_apply_activates_selected_items(self) -> None:
        module = importlib.import_module("api.app.zoopark.forge")
        ctx, session = self._fake_session()
        items = [{"id": "5", "is_active": False}, {"id": "6", "is_active": False}]
        db_items = [SimpleNamespace(id=5, is_active=0), SimpleNamespace(id=6, is_active=0), SimpleNamespace(id=7, is_active=1)]
        session.query.return_value.filter.return_value.all.return_value = db_items
        item_sets = [{"id": "abc", "name": "Сет 1", "icon": "⚒️", "item_ids": ["5", "6"], "is_active": False}]
        with patch.object(module, "get_session", return_value=ctx), \
             patch.object(module, "get_user", return_value=SimpleNamespace(id=9)), \
             patch.object(module, "get_forge_items", return_value=items), \
             patch.object(module, "get_forge_sets", return_value=item_sets), \
             patch.object(module, "bump_data_version"):
            result = module.api_forge_set_apply(1, module.ForgeSetIdBody(set_id="abc"))

        self.assertEqual(result, {"ok": True})
        self.assertEqual([item.is_active for item in db_items], [1, 1, 0])

    def test_top_contract(self) -> None:
        module = importlib.import_module("api.app.zoopark.social")
        ctx, session = self._fake_session()
        user = SimpleNamespace(id=1, id_user=77, nickname="neo")
        users_query = MagicMock()
        users_query.all.return_value = [user]
        me_query = MagicMock()
        me_query.filter.return_value.first.return_value = user
        session.query.side_effect = [users_query, me_query]
        with patch.object(module, "get_session", return_value=ctx), \
             patch.object(module, "active_season", return_value=SimpleNamespace(id=3)), \
             patch.object(module, "calc_pack_income", return_value=1234):
            result = module.api_top(77)
        self.assertEqual(result, {"entries": [{"rank": 1, "tg_id": 77, "nickname": "neo", "income_rub_per_min": 1234, "name_color": None, "is_me": True}], "my_rank": 1})

    def test_clan_request_joins_immediately(self) -> None:
        module = importlib.import_module("api.app.zoopark.social")
        ctx, session = self._fake_session()
        session.get.return_value = SimpleNamespace(idpk=22, name="Wolves")
        user = SimpleNamespace(id=15, unity_id=None)
        with patch.object(module, "get_session", return_value=ctx), \
             patch.object(module, "get_user", return_value=user):
            result = module.api_clan_request(77, module.ClanRequestBody(clan_id=22))
        self.assertEqual(result, {"ok": True, "message": "Вступил в клан «Wolves»"})
        self.assertEqual(user.unity_id, 22)

    def test_mpgame_join_resolves_game_immediately(self) -> None:
        module = importlib.import_module("api.app.zoopark.games")
        ctx, session = self._fake_session()
        game = SimpleNamespace(id=5, status="open", creator_id=1, bet_rub=100, game_type="dice", created_at="2026-01-01T00:00:00+00:00")
        guest = SimpleNamespace(id=9, rub=500, nickname="guest")
        host = SimpleNamespace(id=1, rub=1000, nickname="host")

        def _get(model, key):
            if model is module.MpGame:
                return game
            if model is module.User and key == 1:
                return host
            if model is module.User and key == 9:
                return guest
            return None

        session.get.side_effect = _get
        with patch.object(module, "get_session", return_value=ctx), \
             patch.object(module, "get_user", return_value=guest), \
             patch.object(module, "sync_passive_balance", return_value=(guest, 0, 0)), \
             patch.object(module.random, "randint", side_effect=[6, 2]):
            result = module.api_mpgame_join(77, 5)
        self.assertEqual(result["game"]["status"], "finished")
        self.assertEqual(result["game"]["winner_nickname"], "host")

    def test_mpgame_create_rejects_non_positive_bet(self) -> None:
        module = importlib.import_module("api.app.zoopark.games")

        with self.assertRaises(_FakeHTTPException) as ctx:
            module.api_mpgame_create(77, module.MpCreateBody(game_type="dice", bet_rub=0))

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail, "Ставка должна быть больше нуля")

    def test_start_solo_basketball_returns_history(self) -> None:
        module = importlib.import_module("api.app.zoopark.games")
        ctx, session = self._fake_session()
        user = SimpleNamespace(id=11, rub=1000, nickname="neo")
        session.get.return_value = None

        with patch.object(module, "get_session", return_value=ctx), \
             patch.object(module, "get_user", return_value=user), \
             patch.object(module, "sync_passive_balance", return_value=(user, 0, 0)), \
             patch.object(module.random, "randint", return_value=80), \
             patch.object(module, "_simulate_throw_match", return_value=([{"round": 1, "player_roll": 5, "ai_roll": 4}], 6, 4)):
            result = module.api_start_solo_game(77, module.SoloStartBody(game_type="basketball", bet_rub=100))

        self.assertTrue(result["ok"])
        self.assertEqual(result["result"], "Счёт: 6 — 4")
        self.assertEqual(result["rub_delta"], 100)
        self.assertFalse(result["is_draw"])
        self.assertEqual(result["history"], [{"round": 1, "player_roll": 5, "ai_roll": 4}])

    def test_solo_basketball_uses_playable_roll_bounds(self) -> None:
        module = importlib.import_module("api.app.zoopark.games")

        self.assertEqual(module._solo_roll_bounds("basketball"), (1, 5))
        self.assertEqual(module._solo_roll_bounds("football"), (1, 5))
        self.assertEqual(module._solo_roll_bounds("dice"), (1, 6))

    def test_solo_throw_match_uses_random_round_count(self) -> None:
        module = importlib.import_module("api.app.zoopark.games")

        with patch.object(module.random, "randint", side_effect=[2, 6, 1, 6, 1]) as randint:
            history, player_score, ai_score = module._simulate_throw_match("dice", require_winner=True)

        self.assertEqual(len(history), 2)
        self.assertEqual(player_score, 12)
        self.assertEqual(ai_score, 2)
        self.assertEqual(randint.call_args_list[0].args, (2, 7))

    def test_start_solo_dice_returns_history(self) -> None:
        module = importlib.import_module("api.app.zoopark.games")
        ctx, session = self._fake_session()
        user = SimpleNamespace(id=11, rub=1000, nickname="neo")
        session.get.return_value = None

        with patch.object(module, "get_session", return_value=ctx), \
             patch.object(module, "get_user", return_value=user), \
             patch.object(module, "sync_passive_balance", return_value=(user, 0, 0)), \
             patch.object(module.random, "randint", return_value=20), \
             patch.object(module, "_simulate_throw_match", return_value=([{"round": 1, "player_roll": 4, "ai_roll": 5}], 4, 5)):
            result = module.api_start_solo_game(77, module.SoloStartBody(game_type="dice", bet_rub=100))

        self.assertEqual(result["result"], "Счёт: 4 — 5")
        self.assertFalse(result["won"])
        self.assertEqual(result["rub_delta"], -100)
        self.assertEqual(result["history"], [{"round": 1, "player_roll": 4, "ai_roll": 5}])

    def test_get_expeditions_auto_resolves_expired_active_expedition(self) -> None:
        module = importlib.import_module("api.app.zoopark.progression")
        ctx, session = self._fake_session()
        past = datetime(2020, 1, 1, 0, 0, 0)
        expedition = SimpleNamespace(id=99, status="active", locality=SimpleNamespace(habitat="forest"), started_at="2026-01-01T00:00:00+00:00", ends_at=past, result_json=None)
        localities_query = MagicMock()
        localities_query.filter.return_value.order_by.return_value.all.return_value = [SimpleNamespace(id=1, habitat="forest")]
        expedition_query = MagicMock()
        expedition_query.filter.return_value.order_by.return_value.first.return_value = expedition
        squad_query = MagicMock()
        squad_query.join.return_value.filter.return_value.all.return_value = []
        available_query = MagicMock()
        available_query.filter.return_value.order_by.return_value.all.return_value = []
        session.query.side_effect = [localities_query, expedition_query, squad_query, available_query]
        session.refresh.side_effect = lambda obj: (setattr(obj, "status", "finished"), setattr(obj, "result_json", '{"outcome":"victory","reward_animal_id":null}'))

        with patch.object(module, "get_session", return_value=ctx), \
             patch.object(module, "get_user", return_value=SimpleNamespace(id=8)), \
             patch.object(module, "ensure_player_season", return_value=SimpleNamespace(id=3)), \
             patch.object(module, "resolve_expedition", return_value={"outcome": "victory", "reward_animal_id": None}), \
             patch.object(module, "active_expedition_animal_ids", return_value=[]), \
             patch.object(module, "expire_dead_pack_animals", return_value=None), \
             patch.object(module, "format_pack_animal", side_effect=lambda animal: animal):
            result = module.api_get_expeditions(77)
        self.assertEqual(result["active"]["status"], "finished")
        self.assertEqual(result["active"]["result"], {"outcome": "victory", "reward_animal_id": None})


if __name__ == "__main__":
    unittest.main()
