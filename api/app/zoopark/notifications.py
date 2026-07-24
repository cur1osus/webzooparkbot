"""Transactional Telegram notification events.

Game mutations enqueue plain text messages in the same database transaction as the
mutation. A separate worker is responsible for delivery and retrying temporary Bot API
failures, so a slow or unavailable Telegram endpoint cannot roll back game state.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Sequence
from datetime import date, datetime, timedelta
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.app.core.config import SOCIAL_REWARD_CHAT_ID
from api.app.db.models import Animal, DailyBonus, Expedition, NotificationOutbox, Player, utcnow
from api.app.zoopark import ledger
from api.app.zoopark.catalog import SAFE_DAILY_ATTEMPTS, SAFE_PRIZE_PERCENT
from api.app.zoopark.daily_bonus import roll_daily_bonus_offer
from api.app.zoopark.time import MOSCOW_TIMEZONE, moscow_period_day

KIND_EXPEDITION_FINISHED = "expedition_finished"
KIND_ANIMAL_DEATH = "animal_death"
KIND_DAILY_BONUS_READY = "daily_bonus_ready"
KIND_DISEASE_OUTBREAK = "disease_outbreak"
KIND_SAFE_OPENED = "safe_opened"
KIND_SAFE_CRACKED = "safe_cracked"
def enqueue_chat(
    session: Session,
    *,
    chat_id: int,
    kind: str,
    dedupe_key: str,
    text: str,
) -> bool:
    """Queue one message for a group chat rather than a personal inbox.

    Used for events that belong to everybody at once. One row instead of one per player:
    the community chat is where the game is discussed, and twenty identical DMs are how a
    bot gets muted.
    """
    if not chat_id:
        return False
    if session.scalar(select(NotificationOutbox.id).where(NotificationOutbox.dedupe_key == dedupe_key)) is not None:
        return False
    try:
        with session.begin_nested():
            session.add(
                NotificationOutbox(
                    chat_id=chat_id,
                    kind=kind,
                    dedupe_key=dedupe_key,
                    payload_json=json.dumps({"text": text}, ensure_ascii=False),
                    available_at=utcnow(),
                )
            )
            session.flush()
    except IntegrityError:
        return False
    return True


def enqueue(
    session: Session,
    *,
    player_id: int,
    kind: str,
    dedupe_key: str,
    text: str,
    available_at: datetime | None = None,
) -> None:
    """Add one event unless its business id is already queued.

    Callers hold the player's row lock for mutable game events. The unique key remains
    the final guard for worker scans and any future producer that forgets that lock.
    """
    if session.scalar(select(NotificationOutbox.id).where(NotificationOutbox.dedupe_key == dedupe_key)) is not None:
        return
    try:
        with session.begin_nested():
            session.add(
                NotificationOutbox(
                    player_id=player_id,
                    kind=kind,
                    dedupe_key=dedupe_key,
                    payload_json=json.dumps({"text": text}, ensure_ascii=False),
                    available_at=available_at or utcnow(),
                )
            )
            session.flush()
    except IntegrityError:
        # Another producer won the unique business-event race.
        return


def enqueue_animal_death(session: Session, player: Player, animal: Animal, *, reason: str) -> None:
    label = animal.name or f"животное №{animal.id}"
    enqueue(
        session,
        player_id=player.id,
        kind=KIND_ANIMAL_DEATH,
        dedupe_key=f"animal-death:{animal.id}",
        text=f"💀 {label} погибло. Причина: {reason}.",
    )


def _natural_death_period(animal: Animal) -> date:
    """Return the Moscow calendar day used to group natural-death alerts."""
    if animal.dies_at is None:
        return moscow_period_day(utcnow(), 0)
    return moscow_period_day(animal.dies_at, 0)


def enqueue_animal_death_summary(
    session: Session,
    player: Player,
    animals: Sequence[Animal],
    *,
    reason: str,
) -> None:
    """Queue one digest for all natural deaths in one player's day.

    Natural deaths are a passive, high-volume event: a large zoo can lose thousands of
    animals in the same worker pass. The individual event remains represented by the
    animal's state, while Telegram receives one bounded summary instead of one DM per
    animal. The day-based key also makes the foreground sync and the worker's fallback
    scan idempotent with each other.
    """
    if not animals:
        return

    period = _natural_death_period(animals[0])
    labels = [animal.name or f"животное №{animal.id}" for animal in animals[:3]]
    count = len(animals)
    if count == 1:
        text = f"💀 {labels[0]} погибло. Причина: {reason}."
    else:
        text = f"💀 Погибло животных: {count}. Причина: {reason}."
        text += f" Среди них: {', '.join(labels)}"
        if count > len(labels):
            text += f" и ещё {count - len(labels)}."
        else:
            text += "."

    enqueue(
        session,
        player_id=player.id,
        kind=KIND_ANIMAL_DEATH,
        dedupe_key=f"animal-deaths:{player.id}:{period.isoformat()}",
        text=text,
    )


def enqueue_animal_death_summaries(
    session: Session,
    player: Player,
    animals: Sequence[Animal],
    *,
    reason: str,
) -> None:
    """Group natural deaths by day before creating Telegram notifications."""
    by_period: dict[date, list[Animal]] = defaultdict(list)
    for animal in animals:
        by_period[_natural_death_period(animal)].append(animal)
    for period_animals in by_period.values():
        enqueue_animal_death_summary(session, player, period_animals, reason=reason)


def compact_pending_natural_death_notifications(session: Session, *, limit: int = 5000) -> int:
    """Convert legacy per-animal natural-death rows before they reach Telegram."""
    now = utcnow()
    stale_before = now - timedelta(minutes=5)
    rows = session.scalars(
        select(NotificationOutbox)
        .where(
            NotificationOutbox.kind == KIND_ANIMAL_DEATH,
            NotificationOutbox.dedupe_key.like("animal-death:%"),
            NotificationOutbox.sent_at.is_(None),
            NotificationOutbox.failed_at.is_(None),
            or_(NotificationOutbox.locked_at.is_(None), NotificationOutbox.locked_at < stale_before),
        )
        .order_by(NotificationOutbox.id.asc())
        .limit(limit)
    ).all()

    groups: dict[tuple[int, date], tuple[Player, list[Animal], list[NotificationOutbox]]] = {}
    for row in rows:
        try:
            animal_id = int(row.dedupe_key.removeprefix("animal-death:"))
            text = json.loads(row.payload_json).get("text", "")
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if "естественная смерть" not in text or row.player_id is None:
            continue
        animal = session.get(Animal, animal_id)
        player = session.get(Player, row.player_id)
        if animal is None or player is None or animal.player_id != player.id:
            continue
        key = (player.id, _natural_death_period(animal))
        if key not in groups:
            groups[key] = (player, [], [])
        groups[key][1].append(animal)
        groups[key][2].append(row)

    compacted = 0
    for player, animals, legacy_rows in groups.values():
        enqueue_animal_death_summary(session, player, animals, reason="естественная смерть")
        for row in legacy_rows:
            row.failed_at = now
            row.locked_at = None
            row.last_error = "объединено в сводку смертей"
            compacted += 1
    return compacted


def enqueue_disease_outbreak(session: Session, player: Player, *, count: int, at: datetime) -> None:
    # One event per outbreak instant. Two outbreaks can never share a second (they are gated
    # by elapsed time), so the timestamp is a sufficient business id.
    enqueue(
        session,
        player_id=player.id,
        kind=KIND_DISEASE_OUTBREAK,
        dedupe_key=f"outbreak:{player.id}:{int(at.timestamp())}",
        text=f"🦠 Вспышка болезни в зоопарке! Заболело животных: {count}. Их доход упал вдвое — вылечи их у ветеринара.",
    )


def enqueue_expedition_finished(
    session: Session,
    player: Player,
    expedition: Expedition,
    result: dict | None = None,
) -> None:
    outcome = "победой" if result and result.get("outcome") == "victory" else "поражением"
    text = (
        f"🧭 Экспедиция завершилась {outcome}. Открой зоопарк, чтобы посмотреть результат."
        if result is not None
        else "🧭 Экспедиция завершилась. Открой зоопарк, чтобы посмотреть результат."
    )
    enqueue(
        session,
        player_id=player.id,
        kind=KIND_EXPEDITION_FINISHED,
        dedupe_key=f"expedition-finished:{expedition.id}",
        text=text,
    )


def enqueue_due_expedition_notifications(session: Session, *, limit: int = 500) -> int:
    """Notify players as soon as an unresolved expedition reaches its end time.

    Resolving the fight remains an explicit POST action, so the worker only announces that
    the result is ready. If the player opens the app first, the foreground resolution uses
    the same dedupe key and no duplicate Telegram message is created.
    """
    now = utcnow()
    rows = session.execute(
        select(Expedition, Player)
        .join(Player, Player.id == Expedition.player_id)
        .where(
            Player.status == "active",
            Expedition.resolved_at.is_(None),
            Expedition.ends_at <= now,
        )
        .order_by(Expedition.ends_at.asc(), Expedition.id.asc())
        .limit(limit)
    ).all()
    for expedition, player in rows:
        enqueue_expedition_finished(session, player, expedition)
    return len(rows)


def enqueue_daily_bonus_ready(session: Session, player: Player, bonus_date: date) -> None:
    enqueue(
        session,
        player_id=player.id,
        kind=KIND_DAILY_BONUS_READY,
        dedupe_key=f"daily-bonus:{player.id}:{bonus_date.isoformat()}",
        text="🎁 Ежедневный бонус готов — забери его в зоопарке!",
    )


def enqueue_unclaimed_daily_bonuses(session: Session, *, limit: int = 500) -> int:
    """Materialise today's offers and create one event for every unclaimed offer."""
    today = moscow_period_day(utcnow(), 7)
    players = session.scalars(select(Player).where(Player.status == "active").limit(limit)).all()
    existing_ids = set(
        session.scalars(select(DailyBonus.player_id).where(DailyBonus.bonus_date == today)).all()
    )
    for player in players:
        if player.id in existing_ids:
            continue
        currency, amount, reward_code = roll_daily_bonus_offer(session, player)
        try:
            with session.begin_nested():
                session.add(
                    DailyBonus(
                        player_id=player.id,
                        bonus_date=today,
                        currency=currency,
                        amount=amount,
                        reward_code=reward_code,
                    )
                )
                session.flush()
        except IntegrityError:
            # A request or another worker created today's offer concurrently.
            continue
    offers = session.scalars(
        select(DailyBonus)
        .where(DailyBonus.bonus_date <= today, DailyBonus.claimed_at.is_(None))
        .order_by(DailyBonus.id.asc())
        .limit(limit)
    ).all()
    for offer in offers:
        owner = session.get(Player, offer.player_id)
        if owner is not None:
            enqueue_daily_bonus_ready(session, owner, offer.bonus_date)
    return len(offers)


def enqueue_safe_opened(session: Session) -> bool:
    """Announce the daily safe window in the community chat, once per day.

    The safe is the one feature with a hard deadline, and it is worthless to a player who
    finds out about it at midnight — so it is announced rather than waited for. It goes to
    the chat, not to inboxes: the safe is a shared race, and the chat is where players
    argue about which digits are still possible. The dedupe key is the day, so a worker
    scanning every minute for four hours still posts exactly once.
    """
    # Imported here, not at module scope: `safe` reaches `profile` and `income`, and
    # `income` enqueues notifications, so a top-level import closes that cycle.
    from api.app.zoopark import safe

    now = utcnow()
    if not safe.is_open(now):
        return False
    day, _, closes_at = safe.window(now)
    round_ = safe.current_round(session, now)
    if round_ is None:
        return False

    prize = ledger.treasury_balance(session, "usd") * SAFE_PRIZE_PERCENT // 100
    closes_local = closes_at.astimezone(MOSCOW_TIMEZONE).strftime("%H:%M")
    return enqueue_chat(
        session,
        chat_id=SOCIAL_REWARD_CHAT_ID,
        kind=KIND_SAFE_OPENED,
        dedupe_key=f"safe-open:{day.isoformat()}",
        text=(
            f"🔐 Сейф банка открыт до {closes_local} по Москве. "
            f"В нём ${prize}. У каждого {SAFE_DAILY_ATTEMPTS} попытки назвать код — "
            "все догадки вскроются разом после закрытия."
        ),
    )


def enqueue_safe_cracked(session: Session, result: dict) -> bool:
    """Tell the chat the code fell, who took the money and what the code was."""
    names = ", ".join(payout["nickname"] or "игрок" for payout in result["payouts"]) or "никто"
    return enqueue_chat(
        session,
        chat_id=SOCIAL_REWARD_CHAT_ID,
        kind=KIND_SAFE_CRACKED,
        dedupe_key=f"safe-cracked:{result['round_id']}",
        text=(
            f"💥 Сейф вскрыт! Код был {result['secret']}. "
            f"${result['prize_usd']} забирает {names}. Новый код уже в сейфе — завтра в 19:00."
        ),
    )


def enqueue_natural_death_notifications(session: Session, *, limit: int = 500) -> int:
    """Discover deaths for players who have not opened the app since the animal died."""
    now = utcnow()
    rows = session.execute(
        select(Animal, Player)
        .join(Player, Player.id == Animal.player_id)
        .where(
            Player.status == "active",
            Animal.removed_at.is_(None),
            Animal.dies_at <= now,
        )
        .order_by(Animal.dies_at.asc(), Animal.id.asc())
        .limit(limit)
    ).all()
    by_player: dict[int, tuple[Player, list[Animal]]] = {}
    for animal, player in rows:
        if player.id not in by_player:
            by_player[player.id] = (player, [])
        by_player[player.id][1].append(animal)
    for player, animals in by_player.values():
        enqueue_animal_death_summaries(session, player, animals, reason="естественная смерть")
    return len(rows)
