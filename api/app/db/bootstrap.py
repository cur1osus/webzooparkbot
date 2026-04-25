from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, text

from api.app.db.connection import SessionLocal, engine
from api.app.db.models import AnimalInfo, Base
from api.app.db.tables import (
    ZOOPARK_BOOTSTRAP_META_TABLE,
    ZOOPARK_BREEDING_EVENTS_TABLE,
    ZOOPARK_EXPEDITION_ANIMALS_TABLE,
    ZOOPARK_EXPEDITIONS_TABLE,
    ZOOPARK_FORGE_SET_ITEMS_TABLE,
    ZOOPARK_FORGE_SETS_TABLE,
    ZOOPARK_ITEMS_TABLE,
    ZOOPARK_LOCALITIES_TABLE,
    ZOOPARK_MERCHANT_OFFERS_TABLE,
    ZOOPARK_MP_GAMES_TABLE,
    ZOOPARK_PACK_ANIMALS_TABLE,
    ZOOPARK_PACK_OPENINGS_TABLE,
    ZOOPARK_PLAYER_SEASONS_TABLE,
    ZOOPARK_REFERRALS_TABLE,
    ZOOPARK_SEASONS_TABLE,
    ZOOPARK_SICK_EVENTS_TABLE,
    ZOOPARK_SOLO_STATS_TABLE,
    ZOOPARK_TRANSFER_LINKS_TABLE,
    ZOOPARK_UNITY_TABLE,
    ZOOPARK_USERS_TABLE,
    ZOOPARK_COCKTAIL_SESSIONS_TABLE,
)
from api.app.zoopark.catalog import ANIMALS

MISSING_COLUMN_SQL: Sequence[str] = ()

COPY_COMPAT_TABLES: Sequence[tuple[str, str, tuple[str, ...], tuple[str, ...]]] = (
    (
        "users",
        ZOOPARK_USERS_TABLE,
        ("id", "id_user", "nickname", "date_reg", "paw_coins", "rub", "usd", "sub_on_chat", "sub_on_channel", "bonus"),
        ("unity_id", "is_banned", "balance_seq", "data_version", "bonus_notify_msg_id", "profile_emoji", "last_income_at"),
    ),
    (
        "items",
        ZOOPARK_ITEMS_TABLE,
        ("id", "user_id", "emoji", "name", "lvl", "properties", "rarity", "is_active"),
        (),
    ),
    (
        "unity",
        ZOOPARK_UNITY_TABLE,
        ("idpk", "id", "name", "level", "owner_id"),
        (),
    ),
    (
        "mp_games_new",
        ZOOPARK_MP_GAMES_TABLE,
        ("id", "game_type", "bet_rub", "creator_id", "status", "created_at"),
        ("opponent_id", "creator_score", "opponent_score", "winner_id"),
    ),
    (
        "solo_stats",
        ZOOPARK_SOLO_STATS_TABLE,
        ("user_id", "games_played", "wins", "losses", "total_won", "total_lost"),
        (),
    ),
    (
        "cocktail_sessions",
        ZOOPARK_COCKTAIL_SESSIONS_TABLE,
        ("user_id", "secret", "attempts", "won", "started_at"),
        (),
    ),
    (
        "transfer_links",
        ZOOPARK_TRANSFER_LINKS_TABLE,
        ("id", "link_key", "creator_id", "total_amount", "rub_per_claim", "max_claims", "claims", "active", "created_at"),
        (),
    ),
    (
        "referrals",
        ZOOPARK_REFERRALS_TABLE,
        ("user_id", "referral_id"),
        (),
    ),
)

CANONICAL_TABLES: Sequence[str] = (
    ZOOPARK_USERS_TABLE,
    ZOOPARK_SEASONS_TABLE,
    ZOOPARK_PLAYER_SEASONS_TABLE,
    ZOOPARK_ITEMS_TABLE,
    ZOOPARK_FORGE_SETS_TABLE,
    ZOOPARK_FORGE_SET_ITEMS_TABLE,
    ZOOPARK_UNITY_TABLE,
    ZOOPARK_SICK_EVENTS_TABLE,
    ZOOPARK_MERCHANT_OFFERS_TABLE,
    ZOOPARK_PACK_ANIMALS_TABLE,
    ZOOPARK_PACK_OPENINGS_TABLE,
    ZOOPARK_LOCALITIES_TABLE,
    ZOOPARK_EXPEDITIONS_TABLE,
    ZOOPARK_EXPEDITION_ANIMALS_TABLE,
    ZOOPARK_BREEDING_EVENTS_TABLE,
    ZOOPARK_MP_GAMES_TABLE,
    ZOOPARK_SOLO_STATS_TABLE,
    ZOOPARK_COCKTAIL_SESSIONS_TABLE,
    ZOOPARK_TRANSFER_LINKS_TABLE,
    ZOOPARK_REFERRALS_TABLE,
    ZOOPARK_BOOTSTRAP_META_TABLE,
)


def _table_exists(conn, table: str) -> bool:
    result = conn.execute(
        text("SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME=:t LIMIT 1"),
        {"t": table},
    )
    return result.fetchone() is not None


def _available_columns(conn, table: str) -> set[str]:
    result = conn.execute(
        text("SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME=:t"),
        {"t": table},
    )
    return {str(row[0]) for row in result.fetchall()}


def _column_data_type(conn, table: str, column: str) -> str | None:
    result = conn.execute(
        text("SELECT DATA_TYPE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME=:t AND COLUMN_NAME=:c LIMIT 1"),
        {"t": table, "c": column},
    )
    row = result.fetchone()
    return None if row is None else str(row[0]).lower()


def _ensure_bigint_column(conn, table: str, column: str) -> None:
    if not _table_exists(conn, table):
        return
    if _column_data_type(conn, table, column) == "bigint":
        return
    conn.execute(text(f"ALTER TABLE {table} MODIFY COLUMN {column} BIGINT NOT NULL DEFAULT 0"))
    conn.commit()


def _compat_copy_completed(conn, target_table: str) -> bool:
    if not _table_exists(conn, ZOOPARK_BOOTSTRAP_META_TABLE):
        return False
    result = conn.execute(
        text(f"SELECT 1 FROM {ZOOPARK_BOOTSTRAP_META_TABLE} WHERE target_table=:t LIMIT 1"),
        {"t": target_table},
    )
    return result.fetchone() is not None


def _mark_compat_copy_completed(conn, target_table: str) -> None:
    if not _table_exists(conn, ZOOPARK_BOOTSTRAP_META_TABLE):
        return
    conn.execute(
        text(
            f"INSERT INTO {ZOOPARK_BOOTSTRAP_META_TABLE} (target_table, copied_at) VALUES (:t, NOW()) "
            "ON DUPLICATE KEY UPDATE copied_at=CURRENT_TIMESTAMP"
        ),
        {"t": target_table},
    )


def _copy_compat_table(conn, source_table: str, target_table: str, required: Sequence[str], optional: Sequence[str]) -> None:
    if source_table == target_table or not _table_exists(conn, source_table) or not _table_exists(conn, target_table):
        return
    if _compat_copy_completed(conn, target_table):
        return

    target_columns = _available_columns(conn, target_table)
    source_columns = _available_columns(conn, source_table)
    if not set(required).issubset(target_columns) or not set(required).issubset(source_columns):
        return

    result = conn.execute(text(f"SELECT COUNT(*) FROM {target_table}"))
    if int(result.scalar() or 0) > 0:
        _mark_compat_copy_completed(conn, target_table)
        return

    columns = [c for c in [*required, *optional] if c in target_columns and c in source_columns]
    column_sql = ", ".join(columns)
    conn.execute(text(f"INSERT INTO {target_table} ({column_sql}) SELECT {column_sql} FROM {source_table}"))
    _mark_compat_copy_completed(conn, target_table)


def seed_catalogue(session) -> None:
    count = session.query(func.count(AnimalInfo.id)).scalar() or 0
    if count < len(ANIMALS):
        session.query(AnimalInfo).delete()
        for index, animal in enumerate(ANIMALS, start=1):
            session.add(AnimalInfo(id=index, name=animal["id"], price=animal["price"], income=animal["income"]))


def init_schema() -> None:
    Base.metadata.create_all(engine, checkfirst=True)

    with engine.connect() as conn:
        _ensure_bigint_column(conn, ZOOPARK_USERS_TABLE, "balance_seq")
        for sql in MISSING_COLUMN_SQL:
            try:
                conn.execute(text(sql))
                conn.commit()
            except Exception:
                conn.rollback()
        for source_table, target_table, required, optional in COPY_COMPAT_TABLES:
            _copy_compat_table(conn, source_table, target_table, required, optional)
        conn.commit()

    with SessionLocal() as session:
        seed_catalogue(session)
        session.commit()
