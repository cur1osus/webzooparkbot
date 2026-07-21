"""Every lever a player has, exposed as a tool the model can pull.

One registry, two consumers: the agent loop renders it as OpenAI-style `tools`, and the MCP
server serves the same entries to any MCP client. There is no second implementation of a
game action anywhere — each tool body calls the same `api/app/zoopark/*` service that an
HTTP request from a human calls, with the bot's own `tg_id`. Prices, cooldowns, season
rules and the ledger therefore apply identically; a rival cannot do anything a player
cannot, because there is no other code path for it to do it through.

Two conventions that matter for how well the model plays:

*Refusals are results, not failures.* `HTTPException` is how the services say "too poor",
"on cooldown", "nothing to breed with". It is returned as `{"ok": false, "error": ...}` so
the model reads the reason and adapts. Raising would end the turn over an ordinary "no".

*Descriptions say when to call, not just what it does.* Recent models reach for tools
conservatively; a description that names the trigger condition measurably raises the
should-call rate over one that only names the action.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, cast

from fastapi import HTTPException

from api.app.schemas.core import (
    NicknameColorBody,
    NicknameUpdateBody,
    ProfileAvatarBody,
    ProfileFrameBody,
    ProfileWallpaperBody,
    ThemeBody,
)
from api.app.schemas.development import UpgradeDevelopmentBody
from api.app.schemas.economy import BankExchangeBody
from api.app.schemas.forge import (
    ForgeActivateBody,
    ForgeCreateBody,
    ForgeItemIdBody,
    ForgeMergeBody,
    ForgeSetBody,
    ForgeSetIdBody,
)
from api.app.schemas.games import CocktailGuessBody, DuelCreateBody, SafeGuessBody, SoloStartBody
from api.app.schemas.progression import (
    AssignLocalityBody,
    AssignMatchingLocalityBody,
    BreedBody,
    BuyLocalityBody,
    ReleaseAnimalBody,
    StartExpeditionBody,
    UpgradeLocalityBody,
)
from api.app.schemas.social import (
    ClanCreateBody,
    ClanJoinDecisionBody,
    ClanMemberActionBody,
    ClanRequestBody,
    ClanSpecializationBody,
    TransferCreateBody,
)
from api.app.schemas.status import CureBody
from api.app.zoopark.catalog import (
    COCKTAIL_FRUITS,
    COCKTAIL_LENGTH,
    EXPEDITION_SQUAD_MAX,
    EXPEDITION_SQUAD_MIN,
)
from api.app.zoopark import core as core_service
from api.app.zoopark import development as development_service
from api.app.zoopark import economy as economy_service
from api.app.zoopark import forge as forge_service
from api.app.zoopark import games as games_service
from api.app.zoopark import merchant as merchant_service
from api.app.zoopark import progression as progression_service
from api.app.zoopark import safe as safe_service
from api.app.zoopark import social as social_service
from api.app.zoopark import status as status_service
from api.bots import memory_store

logger = logging.getLogger(__name__)

OBJECT = "object"


@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    properties: dict[str, Any]
    required: list[str] = field(default_factory=list)
    run: Callable[..., Any] = None  # type: ignore[assignment]
    # A tool that only makes sense in some game states can gate its own visibility. The
    # agent evaluates this once at the top of a turn and drops the tool from the list it
    # shows the model when it returns False — a description telling the model "call this only
    # when X" is a request it will ignore, while a tool it cannot see is one it cannot waste
    # a call on. None means always visible. The dispatcher still runs the tool if called, so
    # gating is a hint, never a lock.
    available: Callable[[int, int], bool] | None = None

    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": OBJECT,
                    "properties": self.properties,
                    "required": self.required,
                    "additionalProperties": False,
                },
            },
        }


REGISTRY: dict[str, Tool] = {}


def tool(name: str, description: str, properties: dict | None = None, required: list[str] | None = None,
         available: Callable[[int, int], bool] | None = None):
    def decorate(fn):
        REGISTRY[name] = Tool(name, description, properties or {}, required or [], fn, available)
        return fn

    return decorate


def call(name: str, tg_id: int, player_id: int, arguments: dict) -> dict:
    """Dispatch one tool call. Never raises: the model must see every outcome as data."""
    entry = REGISTRY.get(name)
    if entry is None:
        return {"ok": False, "error": f"нет такого инструмента: {name}"}
    try:
        result = entry.run(tg_id=tg_id, player_id=player_id, **(arguments or {}))
    except HTTPException as exc:
        return {"ok": False, "error": str(exc.detail)}
    except TypeError as exc:  # wrong or missing argument from the model
        return {"ok": False, "error": f"неверные аргументы: {exc}"}
    except ValueError as exc:  # pydantic validation on a body
        return {"ok": False, "error": f"неверное значение: {exc}"}
    except Exception:  # noqa: BLE001 — a broken tool must not end the turn
        logger.exception("tool %s crashed for player %s", name, player_id)
        return {"ok": False, "error": "внутренняя ошибка инструмента"}
    if isinstance(result, dict) and "ok" not in result:
        return {"ok": True, **result}
    return result if isinstance(result, dict) else {"ok": True, "результат": result}


# ── Осмотр ────────────────────────────────────────────────────────────────────


@tool("get_me", "Своё состояние: деньги, доход, содержание, уровни развития, косметика, клан. "
                "Вызывай в начале хода, чтобы понять, с чем работаешь.")
def _get_me(tg_id: int, **_):
    return core_service.me(tg_id)


@tool("list_animals", "Все свои звери с id, генами, средой обитания, здоровьем и тем, где они живут. "
                      "Нужен, чтобы выбрать кого скрещивать, кого отпустить, кого слать в экспедицию.")
def _list_animals(tg_id: int, **_):
    return progression_service.list_available_animals(tg_id)


@tool("list_localities", "Свои локации: уровень, среда, кто в них живёт, цена следующей покупки и апгрейда.")
def _list_localities(tg_id: int, **_):
    return progression_service.list_localities(tg_id)


@tool("get_expeditions", "Идущие экспедиции: где, какая глубина, когда вернутся. Когда добыча "
                         "готова к сбору, появится отдельный инструмент finish_expedition — "
                         "пока его нет, забирать нечего.")
def _get_expeditions(tg_id: int, **_):
    return progression_service.get_expeditions(tg_id)


@tool("packs_info", "Тиры паков, их цены, что уже открыто сегодня и доступен ли бесплатный подарок.")
def _packs_info(tg_id: int, **_):
    return progression_service.packs_info(tg_id)


@tool("merchant_animals", "Предложения торговца: каких зверей и почём он продаёт прямо сейчас.")
def _merchant_animals(tg_id: int, **_):
    return merchant_service.merchant_animals(tg_id)


@tool("get_bank", "Курс рубля к доллару, история курса и сколько у тебя валюты. "
                  "Смотри перед обменом: курс гуляет, и момент имеет значение.")
def _get_bank(tg_id: int, **_):
    return economy_service.bank(tg_id)


@tool("get_bonus", "Сегодняшний ежедневный бонус: что предлагают и забран ли он.")
def _get_bonus(tg_id: int, **_):
    return status_service.daily_bonus(tg_id)


@tool("get_top", "Таблица лидеров по доходу и твоё место в ней.")
def _get_top(tg_id: int, **_):
    return social_service.top(tg_id)


@tool("get_player_profile", "Публичный профиль другого игрока: его зоопарк, доход, достижения. "
                            "Полезно, чтобы понять, чем силён соперник выше тебя в топе.",
      {"target_tg_id": {"type": "integer", "description": "telegram_id игрока из таблицы лидеров"}},
      ["target_tg_id"])
def _get_player_profile(tg_id: int, target_tg_id: int, **_):
    return social_service.public_profile(tg_id, target_tg_id)


@tool("forge_items", "Свои предметы в кузнице: редкость, уровень, свойства, надет ли предмет.")
def _forge_items(tg_id: int, **_):
    return forge_service.forge_items(tg_id)


@tool("forge_sets", "Свои наборы предметов и какой из них активен.")
def _forge_sets(tg_id: int, **_):
    return forge_service.forge_sets(tg_id)


@tool("clan_list", "Список кланов, куда можно попроситься.")
def _clan_list(tg_id: int, **_):
    return social_service.clan_list(tg_id)


@tool("clan_details", "Свой клан: уровень, специализация, требования к следующему уровню.")
def _clan_details(tg_id: int, **_):
    return social_service.clan_details(tg_id)


@tool("clan_members", "Состав своего клана и заявки на вступление, если ты владелец.")
def _clan_members(tg_id: int, **_):
    return social_service.clan_members(tg_id)


@tool("list_duels", "Открытые дуэли, к которым можно присоединиться.")
def _list_duels(tg_id: int, **_):
    return games_service.open_duels(tg_id)


@tool("get_duel", "Одна дуэль подробно: ставка, участники, результат.",
      {"duel_id": {"type": "integer"}}, ["duel_id"])
def _get_duel(tg_id: int, duel_id: int, **_):
    return games_service.get_duel(duel_id, tg_id)


@tool("solo_stats", "Своя статистика по одиночным играм: сыграно, выиграно, баланс.")
def _solo_stats(tg_id: int, **_):
    return games_service.solo_stats(tg_id)


@tool("cocktail_state", "Состояние головоломки с коктейлем: попытки, подсказки, разгадан ли.")
def _cocktail_state(tg_id: int, **_):
    return games_service.cocktail_state(tg_id)


@tool("safe_state", "Сейф банка: открыт ли он сейчас, сколько в нём денег, сколько у тебя осталось попыток "
                    "и доска вскрытых догадок с подсказками. Вызывай в начале хода — окно короткое, "
                    "пропустишь день и потеряешь три попытки.")
def _safe_state(tg_id: int, **_):
    return safe_service.safe_state(tg_id)


@tool("get_referrals", "Свои рефералы и награды за них.")
def _get_referrals(tg_id: int, **_):
    return social_service.referrals(tg_id)


@tool("my_transfers", "Свои переводы: кому отправлял и что забрали.")
def _my_transfers(tg_id: int, **_):
    return social_service.my_transfers(tg_id)


# ── Зоопарк ───────────────────────────────────────────────────────────────────


@tool("claim_daily_gift", "Забрать бесплатный ежедневный подарочный пак. Раз в сутки, тир случайный. "
                          "Всегда бери: это бесплатные звери.")
def _claim_daily_gift(tg_id: int, **_):
    return progression_service.open_pack(tg_id, tier=None)


@tool("claim_daily_bonus", "Забрать ежедневный бонус. Раз в сутки, бесплатно.")
def _claim_daily_bonus(tg_id: int, **_):
    return status_service.claim_bonus(tg_id)


@tool("reroll_daily_bonus", "Перекрутить ежедневный бонус на другой. Тратит перекрутки, если они есть.")
def _reroll_daily_bonus(tg_id: int, **_):
    return status_service.reroll_daily_bonus(tg_id)


@tool("open_pack", "Купить и открыть пак зверей. Лотерея: дорого, зверь случайный. "
                   "Тир выше даёт лучших зверей, но открывается только после покупки тира ниже.",
      {"tier": {"type": "string", "enum": ["rare", "epic", "legendary", "mythic"]},
       "quantity": {"type": "integer", "enum": [1, 5, 10, 50, 100], "description": "сколько паков разом"}},
      ["tier"])
def _open_pack(tg_id: int, tier: str, quantity: int = 1, **_):
    return progression_service.open_pack(tg_id, tier=tier, quantity=quantity)


@tool("merchant_buy", "Купить зверя у торговца по номеру слота из merchant_animals. "
                      "Часто дешевле пака и зверь известен заранее.",
      {"slot": {"type": "integer", "description": "номер слота предложения"}}, ["slot"])
def _merchant_buy(tg_id: int, slot: int, **_):
    return merchant_service.buy_offer(tg_id, slot)


@tool("buy_locality", "Купить новую локацию указанной среды. Каждая следующая дороже в 1.5 раза. "
                      "Зверь в локации своей среды даёт x1.5 дохода.",
      {"habitat": {"type": "string", "enum": ["desert", "mountains", "forest", "fields", "antarctica"]}},
      ["habitat"])
def _buy_locality(tg_id: int, habitat: str, **_):
    return progression_service.buy_locality(tg_id, BuyLocalityBody(habitat=habitat))


@tool("upgrade_locality", "Улучшить локацию. Уровень снижает содержание зверей — вложение вдолгую.",
      {"locality_id": {"type": "integer"}}, ["locality_id"])
def _upgrade_locality(tg_id: int, locality_id: int, **_):
    return progression_service.upgrade_locality(tg_id, UpgradeLocalityBody(locality_id=locality_id))


@tool("assign_animal", "Поселить зверя в локацию. Совпадение среды зверя со средой локации даёт x1.5 "
                       "дохода — зверь не в своей среде это тихая потеря.",
      {"animal_id": {"type": "integer"},
       "locality_id": {"type": "integer", "description": "не указывай, чтобы выселить зверя"}},
      ["animal_id"])
def _assign_animal(tg_id: int, animal_id: int, locality_id: int | None = None, **_):
    return progression_service.assign_locality(
        tg_id, AssignLocalityBody(animal_id=animal_id, locality_id=locality_id)
    )


@tool("assign_matching_animals", "Разом поселить в локацию всех бесхозных зверей её среды. "
                                 "Быстрее, чем по одному, когда только что пришла пачка зверей.",
      {"locality_id": {"type": "integer"}}, ["locality_id"])
def _assign_matching(tg_id: int, locality_id: int, **_):
    return progression_service.assign_matching_locality(
        tg_id, AssignMatchingLocalityBody(locality_id=locality_id)
    )


@tool("breed", "Скрестить двух своих зверей одного вида. Шанс на гены лучше родительских, "
               "но чаще выходит хуже. Каждый зверь скрещивается раз в сутки.",
      {"animal_id_1": {"type": "integer"}, "animal_id_2": {"type": "integer"}},
      ["animal_id_1", "animal_id_2"])
def _breed(tg_id: int, animal_id_1: int, animal_id_2: int, **_):
    return progression_service.breed(tg_id, BreedBody(animal_id_1=animal_id_1, animal_id_2=animal_id_2))


@tool("cure_animal", "Вылечить одного больного зверя. Больной приносит вдвое меньше и заражает соседей.",
      {"animal_id": {"type": "integer"}}, ["animal_id"])
def _cure_animal(tg_id: int, animal_id: int, **_):
    return status_service.cure_animal(tg_id, CureBody(animal_id=animal_id))


@tool("cure_all_animals", "Вылечить всех больных разом. Дороже поштучно, но останавливает эпидемию.")
def _cure_all(tg_id: int, **_):
    return status_service.cure_all_animals(tg_id)


@tool("release_animal", "Отпустить зверя. Содержание растёт с числом зверей, поэтому слабый зверь "
                        "может стоить дороже, чем приносит.",
      {"animal_id": {"type": "integer"}}, ["animal_id"])
def _release_animal(tg_id: int, animal_id: int, **_):
    return progression_service.release_animal(tg_id, ReleaseAnimalBody(animal_id=animal_id))


# ── Экспедиции ────────────────────────────────────────────────────────────────


@tool("start_expedition",
      # The squad bounds come from the catalog rather than a literal: they used to be
      # written here as "1-16", which is not a rule the game has ever enforced, and the
      # model spent calls discovering the real one from refusals.
      f"Отправить зверей в экспедицию. Глубже — больше добычи и предметов, но выше шанс, "
      f"что звери вернутся больными или не вернутся. Отряд: от {EXPEDITION_SQUAD_MIN} до "
      f"{EXPEDITION_SQUAD_MAX} зверей — меньше нельзя. В одной местности одновременно идёт "
      f"только одна экспедиция, и ушедшие звери не приносят дохода, пока не вернутся.",
      {"locality_id": {"type": "integer"},
       "animal_ids": {"type": "array", "items": {"type": "integer"},
                      "minItems": EXPEDITION_SQUAD_MIN, "maxItems": EXPEDITION_SQUAD_MAX,
                      "description": f"{EXPEDITION_SQUAD_MIN}-{EXPEDITION_SQUAD_MAX} своих зверей"},
       "depth": {"type": "integer", "minimum": 1, "maximum": 5}},
      ["locality_id", "animal_ids", "depth"])
def _start_expedition(tg_id: int, locality_id: int, animal_ids: list[int], depth: int, **_):
    return progression_service.start_expedition(
        tg_id, StartExpeditionBody(locality_id=locality_id, animal_ids=animal_ids, depth=depth)
    )


@tool("finish_expedition", "Забрать результат готовой экспедиции.",
      {"expedition_id": {"type": "integer", "description": "не указывай — заберётся самая старая готовая"}},
      # Only shown when a raid has actually landed. The rival used to call this at the top of
      # every turn on the off chance, because a description asking it not to is a description
      # it ignores; hiding the tool until there is something to collect ends the empty call.
      available=lambda tg_id, _player_id: progression_service.has_collectible_expedition(tg_id))
def _finish_expedition(tg_id: int, expedition_id: int | None = None, **_):
    return progression_service.finish_expedition(tg_id, expedition_id)


@tool("dismiss_expedition", "Отменить экспедицию, не забирая результат.",
      {"expedition_id": {"type": "integer"}})
def _dismiss_expedition(tg_id: int, expedition_id: int | None = None, **_):
    return progression_service.dismiss_expedition(tg_id, expedition_id)


# ── Банк и развитие ───────────────────────────────────────────────────────────


@tool("exchange_to_usd", "Обменять рубли на доллары по текущему курсу. Обмен в одну сторону — "
                         "обратно доллары в рубли не превратишь, так что меняй только то, что "
                         "точно потратишь на доллары (паки, кузница, лечение). Курс гуляет: "
                         "посмотри get_bank, там история, и не сливай по дну — обмен по низкому "
                         "курсу это подарок казне. Если курс низкий, а доллары не горят — подожди.",
      {"amount_rub": {"type": "integer", "minimum": 1},
       "exchange_all": {"type": "boolean", "description": "обменять весь рублёвый баланс"}})
def _exchange(tg_id: int, amount_rub: int = 0, exchange_all: bool = False, **_):
    return economy_service.exchange(tg_id, BankExchangeBody(amount_rub=amount_rub, exchange_all=exchange_all))


@tool("upgrade_development", "Прокачать ветеринарию (лечение дешевле), генетику (лучше разведение) "
                             "или экспедиционный корпус (сильнее отряд). Медленные проценты, зато навсегда.",
      {"kind": {"type": "string", "enum": ["vet", "genetics", "expedition"]}}, ["kind"])
# The model hands over a plain string or int; the schema `enum` only suggests. The real
# gate is pydantic, whose ValidationError is a ValueError and comes back to the model as an
# ordinary refusal in `call()` — so the cast states what is already true at runtime.
def _upgrade_development(tg_id: int, kind: str, **_):
    return development_service.upgrade(tg_id, UpgradeDevelopmentBody(kind=cast(Any, kind)))


# ── Кузница ───────────────────────────────────────────────────────────────────


@tool("forge_create", "Выковать новый предмет. Редкость и свойства случайны.",
      {"currency": {"type": "string", "enum": ["usd", "paw"]}})
def _forge_create(tg_id: int, currency: str = "usd", **_):
    return forge_service.forge_create(tg_id, ForgeCreateBody(currency=currency))


@tool("forge_upgrade", "Улучшить предмет на уровень. Шанс успеха падает с уровнем.",
      {"item_id": {"type": "integer"}}, ["item_id"])
def _forge_upgrade(tg_id: int, item_id: int, **_):
    return forge_service.forge_upgrade(tg_id, ForgeItemIdBody(item_id=item_id))


@tool("forge_merge", "Слить два предмета в один, объединив их свойства.",
      {"item_id1": {"type": "integer"}, "item_id2": {"type": "integer"}}, ["item_id1", "item_id2"])
def _forge_merge(tg_id: int, item_id1: int, item_id2: int, **_):
    return forge_service.forge_merge(tg_id, ForgeMergeBody(item_id1=item_id1, item_id2=item_id2))


@tool("forge_sell", "Продать предмет и вернуть часть вложенного.",
      {"item_id": {"type": "integer"}}, ["item_id"])
def _forge_sell(tg_id: int, item_id: int, **_):
    return forge_service.forge_sell(tg_id, ForgeItemIdBody(item_id=item_id))


@tool("forge_activate", "Надеть или снять предмет. Только надетые предметы дают свои бонусы.",
      {"item_id": {"type": "integer"}}, ["item_id"])
def _forge_activate(tg_id: int, item_id: int, **_):
    return forge_service.forge_activate(tg_id, ForgeActivateBody(item_id=item_id))


@tool("forge_set_create", "Создать набор предметов, чтобы надевать их одним действием.",
      {"name": {"type": "string"}, "icon": {"type": "string"},
       "item_ids": {"type": "array", "items": {"type": "integer"}}})
def _forge_set_create(tg_id: int, name: str | None = None, icon: str | None = None,
                      item_ids: list[int] | None = None, **_):
    return forge_service.forge_set_create(tg_id, ForgeSetBody(name=name, icon=icon, item_ids=item_ids or []))


@tool("forge_set_update", "Изменить состав или имя набора.",
      {"set_id": {"type": "integer"}, "name": {"type": "string"}, "icon": {"type": "string"},
       "item_ids": {"type": "array", "items": {"type": "integer"}}}, ["set_id"])
def _forge_set_update(tg_id: int, set_id: int, name: str | None = None, icon: str | None = None,
                      item_ids: list[int] | None = None, **_):
    return forge_service.forge_set_update(
        tg_id, ForgeSetBody(set_id=set_id, name=name, icon=icon, item_ids=item_ids or [])
    )


@tool("forge_set_delete", "Удалить набор.", {"set_id": {"type": "integer"}}, ["set_id"])
def _forge_set_delete(tg_id: int, set_id: int, **_):
    return forge_service.forge_set_delete(tg_id, ForgeSetIdBody(set_id=set_id))


@tool("forge_set_apply", "Надеть весь набор разом.", {"set_id": {"type": "integer"}}, ["set_id"])
def _forge_set_apply(tg_id: int, set_id: int, **_):
    return forge_service.forge_set_apply(tg_id, ForgeSetIdBody(set_id=set_id))


# ── Кланы ─────────────────────────────────────────────────────────────────────


@tool("clan_create", "Основать свой клан.", {"name": {"type": "string", "maxLength": 32}}, ["name"])
def _clan_create(tg_id: int, name: str, **_):
    return social_service.clan_create(tg_id, ClanCreateBody(name=name))


@tool("clan_join", "Подать заявку на вступление в клан.", {"clan_id": {"type": "integer"}}, ["clan_id"])
def _clan_join(tg_id: int, clan_id: int, **_):
    return social_service.clan_join(tg_id, ClanRequestBody(clan_id=clan_id))


@tool("clan_decide_request", "Принять или отклонить заявку в свой клан. Только для владельца.",
      {"request_id": {"type": "integer"}, "decision": {"type": "string", "enum": ["accept", "reject"]}},
      ["request_id", "decision"])
def _clan_decide(tg_id: int, request_id: int, decision: str, **_):
    return social_service.clan_decide_join_request(
        tg_id, ClanJoinDecisionBody(request_id=request_id, decision=cast(Any, decision))
    )


@tool("clan_remove_member", "Исключить участника из своего клана.",
      {"target_tg_id": {"type": "integer"}}, ["target_tg_id"])
def _clan_remove(tg_id: int, target_tg_id: int, **_):
    return social_service.clan_remove_member(tg_id, ClanMemberActionBody(target_tg_id=target_tg_id))


@tool("clan_leave", "Выйти из клана.")
def _clan_leave(tg_id: int, **_):
    return social_service.clan_leave(tg_id)


@tool("clan_level_up", "Поднять уровень клана, если выполнены требования по участникам и доходу.")
def _clan_level_up(tg_id: int, **_):
    return social_service.clan_level_up(tg_id)


@tool("clan_specialization", "Выбрать специализацию клана: она задаёт, какие бонусы получат участники.",
      {"specialization": {"type": "string", "enum": ["specialist", "megapark", "wild"]}},
      ["specialization"])
def _clan_spec(tg_id: int, specialization: str, **_):
    return social_service.clan_choose_specialization(
        tg_id, ClanSpecializationBody(specialization=specialization)
    )


# ── Игры ──────────────────────────────────────────────────────────────────────


@tool("create_duel", "Создать дуэль со ставкой в рублях. Ставка списывается сразу, победитель забирает банк.",
      {"kind": {"type": "string", "description": "вид игры из list_duels"},
       "stake_rub": {"type": "integer", "minimum": 1}},
      ["kind", "stake_rub"])
def _create_duel(tg_id: int, kind: str, stake_rub: int, **_):
    return games_service.create_duel(tg_id, DuelCreateBody(kind=kind, stake=stake_rub, currency="rub"))


@tool("join_duel", "Войти в чужую открытую дуэль.", {"duel_id": {"type": "integer"}}, ["duel_id"])
def _join_duel(tg_id: int, duel_id: int, **_):
    return games_service.join_duel(tg_id, duel_id)


@tool("resolve_duel", "Разыграть дуэль, когда собрались участники.",
      {"duel_id": {"type": "integer"}}, ["duel_id"])
def _resolve_duel(tg_id: int, duel_id: int, **_):
    return games_service.resolve_duel(tg_id, duel_id)


@tool("cancel_duel", "Отменить свою дуэль и вернуть ставку.",
      {"duel_id": {"type": "integer"}}, ["duel_id"])
def _cancel_duel(tg_id: int, duel_id: int, **_):
    return games_service.cancel_duel(tg_id, duel_id)


@tool("start_solo_game", "Сыграть одиночную игру против заведения, поставив процент от баланса.",
      {"kind": {"type": "string"}, "stake_pct": {"type": "integer", "enum": [5, 10, 15]}},
      ["kind"])
def _start_solo(tg_id: int, kind: str, stake_pct: int = 5, **_):
    return games_service.start_solo_game(tg_id, SoloStartBody(kind=kind, stake_pct=cast(Any, stake_pct)))


@tool("cocktail_guess",
      # The palette has to be spelled out: the fruits are emoji, and a model that has only
      # been told "fruits" guesses the words "ананас", "лимон" and burns its whole turn on
      # "Неизвестный фрукт" without ever learning why.
      f"Назвать состав коктейля в ежедневной головоломке. Разгадка даёт награду. "
      f"Ровно {COCKTAIL_LENGTH} фрукта, и только из этого набора: "
      f"{' '.join(COCKTAIL_FRUITS)} — передавай сами эти символы, не их названия. "
      f"Повторы разрешены. Что угадано, смотри в cocktail_state.",
      {"fruits": {"type": "array", "items": {"type": "string", "enum": list(COCKTAIL_FRUITS)},
                  "minItems": COCKTAIL_LENGTH, "maxItems": COCKTAIL_LENGTH,
                  "description": f"ровно {COCKTAIL_LENGTH} символа из {''.join(COCKTAIL_FRUITS)}"}},
      ["fruits"])
def _cocktail_guess(tg_id: int, fruits: list[str], **_):
    return games_service.cocktail_guess(tg_id, CocktailGuessBody(fruits=fruits))


@tool("safe_guess", "Назвать код сейфа банка. Сначала смотри доску в safe_state и подбирай код, "
                    "который не противоречит ни одной опубликованной подсказке. Если доска пуста, "
                    "подсказок нет — это чистая лотерея, а попыток в день всего несколько; не трать "
                    "их вслепую, дождись, пока на доске появятся чужие догадки. Ответа на свою "
                    "попытку сразу не будет — подсказка придёт вместе со всеми после закрытия окна.",
      {"code": {"type": "string", "description": "4 цифры, например 0473"}},
      ["code"],
      # Only shown while the safe is open and a guess remains. Closed, it cannot be used at
      # all; the rival used to spend a round finding that out.
      available=lambda tg_id, _player_id: safe_service.has_open_attempt(tg_id))
def _safe_guess(tg_id: int, code: str, **_):
    return safe_service.safe_guess(tg_id, SafeGuessBody(code=code))


# ── Профиль и косметика ───────────────────────────────────────────────────────


@tool("set_nickname", "Сменить себе ник.", {"nickname": {"type": "string", "maxLength": 32}}, ["nickname"])
def _set_nickname(tg_id: int, nickname: str, **_):
    return core_service.update_nickname(tg_id, NicknameUpdateBody(nickname=nickname))


@tool("set_theme", "Сменить тему оформления профиля.", {"theme": {"type": "string"}}, ["theme"])
def _set_theme(tg_id: int, theme: str, **_):
    return core_service.set_theme(tg_id, ThemeBody(theme=theme))


@tool("set_nickname_color", "Надеть купленный цвет ника.", {"color": {"type": "string"}}, ["color"])
def _set_color(tg_id: int, color: str, **_):
    return core_service.set_nickname_color(tg_id, NicknameColorBody(color=color))


@tool("buy_nickname_color", "Купить цвет ника.", {"color": {"type": "string"}}, ["color"])
def _buy_color(tg_id: int, color: str, **_):
    return core_service.buy_nickname_color(tg_id, color)


@tool("set_profile_frame", "Надеть купленную рамку аватара.", {"frame": {"type": "string"}}, ["frame"])
def _set_frame(tg_id: int, frame: str, **_):
    return core_service.set_profile_frame(tg_id, ProfileFrameBody(frame=frame))


@tool("buy_profile_frame", "Купить рамку аватара.", {"frame": {"type": "string"}}, ["frame"])
def _buy_frame(tg_id: int, frame: str, **_):
    return core_service.buy_profile_frame(tg_id, frame)


@tool("set_profile_wallpaper", "Надеть купленные обои профиля.",
      {"wallpaper": {"type": "string"}}, ["wallpaper"])
def _set_wallpaper(tg_id: int, wallpaper: str, **_):
    return core_service.set_profile_wallpaper(tg_id, ProfileWallpaperBody(wallpaper=wallpaper))


@tool("buy_profile_wallpaper", "Купить обои профиля.", {"wallpaper": {"type": "string"}}, ["wallpaper"])
def _buy_wallpaper(tg_id: int, wallpaper: str, **_):
    return core_service.buy_profile_wallpaper(tg_id, wallpaper)


@tool("set_profile_avatar", "Поставить в профиль открытое достижение как аватар. "
                            "Без аватара показывается случайное животное.",
      {"achievement_id": {"type": "string", "description": "id открытого достижения"}},
      ["achievement_id"])
def _set_avatar(tg_id: int, achievement_id: str, **_):
    avatar = f"{core_service.PROFILE_ACHIEVEMENT_PREFIX}{achievement_id}"
    return core_service.set_profile_avatar(tg_id, ProfileAvatarBody(avatar=avatar))


# ── Переводы ──────────────────────────────────────────────────────────────────


@tool("create_transfer", "Создать перевод рублей по коду, который смогут забрать другие игроки. "
                         "Деньги уходят из твоего баланса сразу.",
      {"total_rub": {"type": "integer", "minimum": 1},
       "max_claims": {"type": "integer", "minimum": 1, "maximum": 100}},
      ["total_rub", "max_claims"])
def _create_transfer(tg_id: int, total_rub: int, max_claims: int, **_):
    return social_service.transfers_create(
        tg_id, TransferCreateBody(total_rub=total_rub, max_claims=max_claims)
    )


@tool("claim_transfer", "Забрать чужой перевод по коду.", {"code": {"type": "string"}}, ["code"])
def _claim_transfer(tg_id: int, code: str, **_):
    return social_service.transfer_claim(tg_id, code)


# ── Память и завершение хода ──────────────────────────────────────────────────


@tool("remember", "Записать себе вывод на будущее: что сработало, что оказалось ошибкой, "
                  "к чему ты идёшь. Эти заметки ты увидишь в начале следующего хода. "
                  "Не записывай баланс, доход и прочее, что и так видно инструментами — "
                  "к следующему ходу это устареет, а место в блокноте вытеснит нужное. "
                  "Одна заметка за ход, и только если узнал что-то новое.",
      {"note": {"type": "string", "description": "один вывод, коротко"}}, ["note"])
def _remember(player_id: int, note: str, **_):
    return memory_store.remember(player_id, note)


@tool("read_memory", "Перечитать свои заметки. Они и так даются в начале хода — "
                     "вызывай, только если нужно свериться ещё раз.")
def _read_memory(player_id: int, **_):
    return {"заметки": memory_store.load(player_id)}


@tool("forget", "Удалить свою заметку по номеру, если она устарела или оказалась неверной.",
      {"index": {"type": "integer", "description": "номер заметки в квадратных скобках"}}, ["index"])
def _forget(player_id: int, index: int, **_):
    return memory_store.forget(player_id, index)


@tool("end_turn", "Закончить ход. Вызывай, когда сделал всё, что хотел — "
                  "не обязательно тратить весь лимит вызовов.",
      {"summary": {"type": "string", "description": "одной фразой: что сделал и почему"}}, ["summary"])
def _end_turn(summary: str, **_):
    return {"ok": True, "ход_завершён": True, "итог": summary}


def schemas(tg_id: int | None = None, player_id: int | None = None) -> list[dict]:
    """The toolset to hand the model. With a player's ids, tools that gate their own
    visibility are dropped when they would do nothing in the current game state; without
    ids (the MCP server, tests) every tool is returned. A gate that raises is treated as
    "show it" — a bug in a predicate must not hide a working tool."""
    entries = []
    for entry in REGISTRY.values():
        if entry.available is not None and tg_id is not None and player_id is not None:
            try:
                if not entry.available(tg_id, player_id):
                    continue
            except Exception:
                logger.exception("gate for %s raised; showing it", entry.name)
        entries.append(entry.schema())
    return entries
