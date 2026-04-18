#!/usr/bin/env python3
"""
ZooPark MCP Server — Model Context Protocol interface for the ZooPark game.
Allows LLMs to interact with ZooPark through the web API.

Запуск:
  ZOOPARK_SESSION=<token> python api/mcp_server.py

Или через uvx (нужен mcp+httpx):
  uvx --with httpx mcp run api/mcp_server.py

Настройка в Claude Desktop (claude_desktop_config.json):
  {
    "mcpServers": {
      "zoopark": {
        "command": "/home/maxggor/.local/share/uv/tools/kimi-cli/bin/python",
        "args": ["/home/maxggor/Desktop/webzooparkbot/api/mcp_server.py"],
        "env": {
          "ZOOPARK_SESSION": "<your-session-token>"
        }
      }
    }
  }

Аутентификация:
  1. Установить ZOOPARK_SESSION через env
  2. Или вызвать инструмент `login` — он сохранит токен в памяти сервера
"""

import json
import os
import re
import tempfile
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

BASE_URL = os.getenv("ZOOPARK_API_URL", "https://89-22-224-52.sslip.io:8443")

mcp = FastMCP("ZooPark")

# Токен сессии — из env или через инструмент login
_session_token: str = os.getenv("ZOOPARK_SESSION", "")


def _headers() -> dict[str, str]:
    h: dict[str, str] = {}
    if _session_token:
        h["X-Web-Session"] = _session_token
    return h


def _api(method: str, path: str, body: dict | None = None) -> Any:
    """Вызов ZooPark API. Возвращает dict или {error: ...}."""
    url = f"{BASE_URL}{path}"
    try:
        with httpx.Client(verify=False, timeout=30) as client:
            if method == "GET":
                resp = client.get(url, headers=_headers())
            else:
                resp = client.post(url, json=body or {}, headers=_headers())
    except httpx.RequestError as e:
        return {"error": f"Сетевая ошибка: {e}"}

    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text}

    if resp.status_code >= 400:
        detail = data.get("detail", data) if isinstance(data, dict) else data
        return {"error": detail, "status_code": resp.status_code}
    return data


def _fmt(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2)


# ─── Аутентификация ───────────────────────────────────────────────────────────


@mcp.tool()
def login(login: str, password: str) -> str:
    """
    Войти в игру по логину и паролю (web-аккаунт).
    Токен сохраняется в памяти сервера для последующих вызовов.
    Создать web-аккаунт можно в разделе «Ещё» → «Web-доступ» в приложении.
    """
    global _session_token
    data = _api("POST", "/api/web-auth/login", {"login": login, "password": password})
    if isinstance(data, dict) and data.get("token"):
        _session_token = data["token"]
        return _fmt(
            {
                "ok": True,
                "message": "Авторизован успешно. Токен сохранён.",
                "token": data["token"],
            }
        )
    return _fmt(data)


# ─── Состояние игры ───────────────────────────────────────────────────────────


@mcp.tool()
def get_game_state() -> str:
    """
    Полное состояние игрока: баланс (RUB/USD/PawCoins), животные в зоопарке,
    вольеры, предметы, больные животные, доход в минуту, клан, статус бонуса.
    Используй это как отправную точку перед принятием решений.
    """
    return _fmt(_api("GET", "/api/me"))


@mcp.tool()
def get_balance() -> str:
    """Текущий баланс игрока: RUB, USD, PawCoins."""
    return _fmt(_api("GET", "/api/balance"))


@mcp.tool()
def get_top() -> str:
    """Таблица лидеров — топ-20 игроков по доходу в минуту."""
    return _fmt(_api("GET", "/api/top"))


@mcp.tool()
def get_profile(user_id: int) -> str:
    """Публичный профиль игрока по его Telegram user_id."""
    return _fmt(_api("GET", f"/api/top/profile/{user_id}"))


@mcp.tool()
def get_online_players() -> str:
    """Список игроков онлайн прямо сейчас (до 50 человек)."""
    return _fmt(_api("GET", "/api/online/players"))


@mcp.tool()
def get_achievements() -> str:
    """Достижения игрока: полученные и прогресс по текущим."""
    return _fmt(_api("GET", "/api/achievements"))


@mcp.tool()
def get_referrals() -> str:
    """Реферальная программа: приглашённые друзья и заработанные бонусы."""
    return _fmt(_api("GET", "/api/referrals"))


# ─── Зоопарк: животные и вольеры ─────────────────────────────────────────────


@mcp.tool()
def buy_animal(code: str, qty: int = 1) -> str:
    """
    Купить животное за USD. Цена растёт с количеством (×15% за каждый milestone 10, 100, 1000...).
    Нужны свободные места в вольерах. Коды животных: animal1_rare, animal2_epic и т.д.
    Перед покупкой проверь баланс и свободные места через get_game_state.
    """
    return _fmt(
        _api(
            "POST",
            "/api/buy_animal",
            {
                "code": code,
                "qty_mantissa": str(max(1, qty)),
                "qty_exponent": 0,
            },
        )
    )


@mcp.tool()
def sell_animal(code: str, qty: int = 1) -> str:
    """
    Продать животное из зоопарка за RUB.
    Доход в минуту снизится — продавай с умом.
    """
    return _fmt(
        _api(
            "POST",
            "/api/sell_animal",
            {
                "code": code,
                "qty_mantissa": str(max(1, qty)),
                "qty_exponent": 0,
            },
        )
    )


@mcp.tool()
def buy_aviary(code: str, qty: int = 1) -> str:
    """
    Купить вольер за USD. Добавляет места для животных.
    Коды: aviary1 (малый), aviary2 (средний), aviary3 (большой).
    """
    return _fmt(
        _api(
            "POST",
            "/api/buy_aviary",
            {
                "code": code,
                "qty_mantissa": str(max(1, qty)),
                "qty_exponent": 0,
            },
        )
    )


@mcp.tool()
def cure_animal(event_id: int) -> str:
    """
    Вылечить больное животное (стоит RUB).
    event_id берётся из get_game_state → sick_animals[].idpk / event_id.
    Больные животные снижают доход — лечи как можно скорее.
    """
    return _fmt(_api("POST", "/api/cure_animal", {"event_id": event_id}))


# ─── Банк ─────────────────────────────────────────────────────────────────────


@mcp.tool()
def get_bank_info() -> str:
    """
    Информация о банке: курс обмена RUB→USD, сколько RUB нужно на 1 USD,
    реферальный бонус к курсу.
    """
    return _fmt(_api("GET", "/api/bank"))


@mcp.tool()
def exchange_currency(amount: int = 0, exchange_all: bool = False) -> str:
    """
    Обменять рубли на доллары через банк.
    amount — сумма в RUB (если exchange_all=False).
    exchange_all=True — обменять весь баланс RUB.
    Курс смотри в get_bank_info.
    """
    body: dict = {"all": exchange_all}
    if not exchange_all and amount > 0:
        body["amount_mantissa"] = str(amount)
        body["amount_exponent"] = 0
    return _fmt(_api("POST", "/api/bank/exchange", body))


# ─── Ежедневный бонус ─────────────────────────────────────────────────────────


@mcp.tool()
def claim_daily_bonus(action: str = "preview") -> str:
    """
    Ежедневный бонус (доступен раз в сутки, сбрасывается в 11:00 МСК).
    action:
      'preview'  — посмотреть что выпало (без получения)
      'confirm'  — получить бонус
      'reroll'   — перебросить (если есть перебросы)
      'claim'    — получить сразу без предпросмотра
    Рекомендуемый порядок: preview → confirm (или reroll → confirm).
    """
    return _fmt(_api("POST", "/api/claim_bonus", {"action": action}))


# ─── Торговец ─────────────────────────────────────────────────────────────────


@mcp.tool()
def get_merchant() -> str:
    """
    Предложения случайного торговца (обновляются раз в сутки).
    Торговец предлагает животных из зоопарка игрока — три слота с разными ценами.
    """
    return _fmt(_api("GET", "/api/merchant/animals"))


@mcp.tool()
def buy_from_merchant(slot: int) -> str:
    """
    Купить у торговца.
    slot 1 — за RUB (обычная цена)
    slot 2 — скидка за PawCoins
    slot 3 — особое предложение за PawCoins
    Сначала проверь get_merchant чтобы узнать что доступно.
    """
    if slot not in (1, 2, 3):
        return _fmt({"error": "slot должен быть 1, 2 или 3"})
    return _fmt(_api("POST", f"/api/merchant/buy{slot}"))


# ─── Соло-игры ────────────────────────────────────────────────────────────────


@mcp.tool()
def get_solo_stats() -> str:
    """Статистика соло-игр: побед, поражений, сумма выигрышей за сегодня."""
    return _fmt(_api("GET", "/api/solo-stats"))


@mcp.tool()
def start_solo_game(game_type: str, bet_amount: int, currency: str) -> str:
    """
    Начать соло-игру в кости против AI.
    game_type: 'dice' (кубики 1-6), 'coin' (орёл/решка), 'dart' (дартс)
    currency: 'rub' или 'usd'
    bet_amount: сумма ставки (списывается сразу)
    После старта делай броски через throw_solo_game пока moves_left > 0.
    Максимальная ставка = 1 час дохода, дневной лимит = 5 часов дохода.
    """
    return _fmt(
        _api(
            "POST",
            "/api/solo-game/start",
            {
                "game_type": game_type,
                "bet_amount_mantissa": str(max(1, bet_amount)),
                "bet_amount_exponent": 0,
                "currency": currency,
            },
        )
    )


@mcp.tool()
def throw_solo_game() -> str:
    """
    Сделать бросок в активной соло-игре.
    Повторяй вызов пока moves_left > 0.
    Когда finished=true: won=true — победа (ставка×2), won=false — поражение.
    """
    return _fmt(_api("POST", "/api/solo-game/throw"))


# ─── Кланы ───────────────────────────────────────────────────────────────────


@mcp.tool()
def get_clan_list() -> str:
    """Список всех кланов: название, уровень, рейтинг, количество участников."""
    return _fmt(_api("GET", "/api/clan/list"))


@mcp.tool()
def get_clan_members() -> str:
    """Список участников своего клана с их доходом."""
    return _fmt(_api("GET", "/api/clan/members"))


@mcp.tool()
def get_clan_progress() -> str:
    """Прогресс клана: очки до следующего уровня, вклад участников."""
    return _fmt(_api("GET", "/api/clan/progress"))


# ─── Переводы ────────────────────────────────────────────────────────────────


@mcp.tool()
def create_transfer(currency: str, amount: int, max_claims: int = 1) -> str:
    """
    Создать ссылку для раздачи денег другим игрокам.
    currency: 'rub', 'usd' или 'paw_coins'
    amount: сумма для одного получателя
    max_claims: максимальное число получателей (1–100)
    Возвращает transfer_key — ссылку для отправки другим.
    """
    return _fmt(
        _api(
            "POST",
            "/api/transfers/create",
            {
                "currency": currency,
                "amount_mantissa": str(max(1, amount)),
                "amount_exponent": 0,
                "max_claims": max(1, min(100, max_claims)),
            },
        )
    )


@mcp.tool()
def get_my_transfers() -> str:
    """Мои активные раздачи денег: ключи, валюта, сколько осталось получателей."""
    return _fmt(_api("GET", "/api/my-transfers"))


# ─── Мультиплеер ─────────────────────────────────────────────────────────────


@mcp.tool()
def get_open_mp_games() -> str:
    """Список открытых мультиплеерных игр в кости — можно присоединиться."""
    return _fmt(_api("GET", "/api/mpgame/open"))


@mcp.tool()
def create_mp_game(
    game_type: str, award: int, currency: str, amount_gamers: int = 2
) -> str:
    """
    Создать мультиплеерную игру.
    game_type: 'dice', 'dart', 'bowling', 'football', 'basketball'
    award: призовой фонд (min 1000 RUB / 5 USD)
    currency: 'rub' или 'usd'
    amount_gamers: 2–80 игроков
    Возвращает game_id и share_link для приглашения.
    """
    return _fmt(
        _api(
            "POST",
            "/api/mpgame/create",
            {
                "game_type": game_type,
                "amount_gamers": max(2, min(80, amount_gamers)),
                "amount_award_mantissa": str(max(1, award)),
                "amount_award_exponent": 0,
                "currency": currency,
            },
        )
    )


@mcp.tool()
def join_mp_game(game_id: str) -> str:
    """
    Присоединиться к открытой MP-игре по game_id из get_open_mp_games.
    Ставка автоматически списывается.
    """
    return _fmt(_api("POST", f"/api/mpgame/{game_id}/join"))


@mcp.tool()
def throw_mp_game(game_id: str) -> str:
    """
    Бросить кубик в MP-игре. Повторяй пока moves_left > 0.
    Игра завершается когда все участники сделали все броски.
    """
    return _fmt(_api("POST", f"/api/mpgame/{game_id}/throw"))


# ─── Кузница ─────────────────────────────────────────────────────────────────


@mcp.tool()
def get_forge_items() -> str:
    """
    Список предметов игрока (поле items[] в ответе /api/me).
    Каждый предмет имеет: id_item, name, rarity, lvl, is_active, props.

    Значения свойств (props):
      general_income   — +% ко всему доходу в минуту (самый ценный стат)
      exchange_bank    — скидка % на курс обмена RUB→USD (макс 80%)
      aviaries_sale    — скидка % на покупку вольеров (макс 80%)
      animal_income    — +% к доходу конкретного вида животного
      animal_sale      — скидка % на покупку конкретного животного (макс 80%)
      extra_moves      — доп. броски в играх (кости/дартс)
      last_chance      — шанс не потерять ставку при проигрыше
      bonus_changer    — влияет на ежедневный бонус

    Редкость по числу свойств: common=1, rare=2, epic=3, mythical=4.
    Макс 3 активных предмета одновременно.
    """
    return _fmt(_api("GET", "/api/me"))


@mcp.tool()
def forge_create(currency: str = "usd") -> str:
    """
    Создать новый случайный предмет в кузнице.
    currency: 'usd' (базово $100, +20% за каждый следующий предмет)
              'paw' (фиксированно 350 PawCoins)

    Свойства предмета случайные. Приоритет по ценности:
      1. general_income — +% ко всему доходу (лучший стат)
      2. exchange_bank  — скидка на обмен RUB→USD
      3. aviaries_sale  — скидка на вольеры
      4. animal_income  — бонус к конкретному виду
      5. animal_sale    — скидка на конкретное животное
      6. extra_moves / last_chance / bonus_changer — игровые бонусы

    Редкость: common(1 стат) < rare(2) < epic(3) < mythical(4 стата).
    Легендарные(5 статов) нельзя улучшать и объединять.
    Возвращает: item (id_item, name, rarity, lvl, properties), new_price, spent_amount.
    """
    return _fmt(_api("POST", "/api/forge/create", {"currency": currency}))


@mcp.tool()
def forge_upgrade(item_id: str) -> str:
    """
    Улучшить предмет (+1 уровень, усиливает одно свойство).
    item_id — строка UUID из get_forge_items → items[].id_item.
    Стоимость: $50 × (текущий_уровень + 1). Макс уровень 12.
    Шанс успеха снижается на 10% за каждый уровень (lvl 0 = 100%, lvl 10 = 0%).
    Возвращает: upgraded (bool), item, new_usd, message.
    """
    return _fmt(_api("POST", "/api/forge/upgrade", {"item_id": item_id}))


@mcp.tool()
def forge_activate(item_id: str, is_active: bool) -> str:
    """
    Активировать или деактивировать предмет кузницы.
    Активные предметы применяют свои бонусы (макс 3 одновременно).
    item_id — UUID из get_forge_items → items[].id_item.
    is_active: true — активировать, false — деактивировать.

    Стратегия активации (по приоритету):
      1. general_income — активировать всегда (буст всего дохода)
      2. exchange_bank  — активировать если часто меняешь RUB→USD
      3. aviaries_sale  — активировать перед покупкой вольеров
      4. animal_income/animal_sale — если есть много животных этого вида
    """
    return _fmt(
        _api(
            "POST",
            "/api/forge/activate",
            {
                "item_id": item_id,
                "is_active": is_active,
            },
        )
    )


@mcp.tool()
def forge_merge(item_id_1: str, item_id_2: str) -> str:
    """
    Объединить два предмета в один новый (с комбинированными свойствами).
    item_id_1, item_id_2 — UUID из get_forge_items → items[].id_item.
    Нельзя объединять легендарные предметы (≥5 свойств).
    Стоимость: $30 × (кол-во свойств обоих + сумма уровней).
    Возвращает: item (новый объединённый), new_usd, new_price.
    """
    return _fmt(
        _api(
            "POST",
            "/api/forge/merge",
            {
                "item_id_1": item_id_1,
                "item_id_2": item_id_2,
            },
        )
    )


# ─── Память агента ───────────────────────────────────────────────────────────

MEMO_HISTORY_LIMIT = int(os.getenv("ZOOPARK_AI_MEMO_HISTORY_LIMIT", "20"))
MEMO_MAX_BYTES = int(os.getenv("ZOOPARK_AI_MEMO_MAX_BYTES", str(64 * 1024)))


def _memo_file_path() -> str:
    custom_path = os.getenv("ZOOPARK_AI_MEMO_FILE", "").strip()
    if custom_path:
        return custom_path

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    memo_dir = os.path.join(base_dir, "agent_memos")
    memo_id = (
        os.getenv("ZOOPARK_AI_MEMO_ID")
        or os.getenv("ZOOPARK_AI_LOCK_ID")
        or os.getenv("ZOOPARK_AI_NAME")
        or (_session_token[:16] if _session_token else "")
        or "default"
    )
    safe_id = re.sub(r"[^a-zA-Z0-9_.-]+", "_", memo_id).strip("._-")[:48] or "default"
    return os.path.join(memo_dir, f"{safe_id}.json")


MEMO_FILE = _memo_file_path()


def _normalize_memo(memo: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(memo, dict):
        raise ValueError("memo must be a JSON object")

    normalized = dict(memo)
    history = normalized.get("history")
    if history is not None:
        if not isinstance(history, list):
            raise ValueError("memo.history must be a list")
        if len(history) > MEMO_HISTORY_LIMIT:
            normalized["history"] = history[-MEMO_HISTORY_LIMIT:]

    try:
        payload = json.dumps(normalized, ensure_ascii=False, indent=2)
    except TypeError as e:
        raise ValueError(f"memo is not JSON-serializable: {e}") from e

    if len(payload.encode("utf-8")) > MEMO_MAX_BYTES:
        raise ValueError(f"memo exceeds {MEMO_MAX_BYTES} bytes")

    return normalized


def _load_memo() -> dict[str, Any]:
    try:
        with open(MEMO_FILE, "r", encoding="utf-8") as f:
            raw = f.read().strip()
    except FileNotFoundError:
        return {}

    if not raw:
        return {}

    data = json.loads(raw)
    return _normalize_memo(data)


def _write_memo_atomic(memo: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_memo(memo)
    memo_dir = os.path.dirname(MEMO_FILE) or "."
    os.makedirs(memo_dir, exist_ok=True)

    fd, temp_path = tempfile.mkstemp(prefix="memo_", suffix=".tmp", dir=memo_dir)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(normalized, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, MEMO_FILE)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    return normalized


@mcp.tool()
def read_memo() -> str:
    """
    Прочитать свои заметки из памяти.
    Вызывай в начале хода чтобы вспомнить что было важно.
    """
    try:
        return _fmt(_load_memo())
    except FileNotFoundError:
        return _fmt({})
    except (json.JSONDecodeError, ValueError) as e:
        return _fmt({"error": f"memo corrupted: {e}", "memo_file": MEMO_FILE})


@mcp.tool()
def write_memo(memo: dict) -> str:
    """
    Записать заметки в память (перезаписывает полностью).
    Сохраняй что считаешь важным: ранг, цели, ID игр, планы, наблюдения.
    memo — произвольный JSON-объект с любыми ключами.
    """
    try:
        normalized = _write_memo_atomic(memo)
    except (TypeError, ValueError) as e:
        return _fmt({"ok": False, "error": str(e), "memo_file": MEMO_FILE})
    return _fmt({"ok": True, "memo_file": MEMO_FILE, "memo": normalized})


@mcp.tool()
def update_memo_fields(updates: dict, remove_keys: list[str] | None = None) -> str:
    """
    Частично обновить память без полной перезаписи файла.
    updates — ключи верхнего уровня для добавления/замены.
    remove_keys — необязательный список ключей верхнего уровня для удаления.
    """
    if not isinstance(updates, dict):
        return _fmt(
            {
                "ok": False,
                "error": "updates must be a JSON object",
                "memo_file": MEMO_FILE,
            }
        )

    try:
        memo = _load_memo()
        memo.update(updates)

        for key in remove_keys or []:
            if isinstance(key, str):
                memo.pop(key, None)

        normalized = _write_memo_atomic(memo)
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        return _fmt({"ok": False, "error": str(e), "memo_file": MEMO_FILE})

    return _fmt({"ok": True, "memo_file": MEMO_FILE, "memo": normalized})


@mcp.tool()
def append_memo_history(entry: Any) -> str:
    """
    Добавить одну запись в memo.history.
    История автоматически обрезается до последних N записей.
    """
    try:
        memo = _load_memo()
        history = memo.get("history")
        if history is None:
            history = []
        if not isinstance(history, list):
            return _fmt(
                {
                    "ok": False,
                    "error": "memo.history must be a list",
                    "memo_file": MEMO_FILE,
                }
            )

        history.append(entry)
        memo["history"] = history
        normalized = _write_memo_atomic(memo)
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        return _fmt({"ok": False, "error": str(e), "memo_file": MEMO_FILE})

    return _fmt(
        {
            "ok": True,
            "memo_file": MEMO_FILE,
            "history_len": len(normalized.get("history", [])),
        }
    )


if __name__ == "__main__":
    mcp.run(transport="stdio")
