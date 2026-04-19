from __future__ import annotations

from collections.abc import Sequence

from api.app.zoopark.catalog import ANIMALS, AVIARIES
from api.app.zoopark.db_tables import (
    ZOOPARK_ANIMALS_TABLE,
    ZOOPARK_AVIARIES_TABLE,
    ZOOPARK_COCKTAIL_SESSIONS_TABLE,
    ZOOPARK_EXPEDITION_ANIMALS_TABLE,
    ZOOPARK_EXPEDITIONS_TABLE,
    ZOOPARK_EXTRA_TABLE,
    ZOOPARK_ITEMS_TABLE,
    ZOOPARK_LOCALITIES_TABLE,
    ZOOPARK_MERCHANTS_TABLE,
    ZOOPARK_MP_GAMES_TABLE,
    ZOOPARK_PACK_ANIMALS_TABLE,
    ZOOPARK_REFERRALS_TABLE,
    ZOOPARK_SICK_EVENTS_TABLE,
    ZOOPARK_SOLO_STATS_TABLE,
    ZOOPARK_TRANSFER_LINKS_TABLE,
    ZOOPARK_UNITY_TABLE,
    ZOOPARK_USERS_TABLE,
)
from api.app.zoopark.runtime import get_db


CREATE_TABLES_SQL: Sequence[str] = (
    f"""CREATE TABLE IF NOT EXISTS {ZOOPARK_USERS_TABLE} (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        id_user BIGINT NOT NULL UNIQUE,
        nickname VARCHAR(64) NOT NULL,
        date_reg DATETIME NOT NULL,
        paw_coins BIGINT NOT NULL DEFAULT 0,
        rub BIGINT NOT NULL DEFAULT 0,
        usd BIGINT NOT NULL DEFAULT 0,
        sub_on_chat TINYINT(1) NOT NULL DEFAULT 0,
        sub_on_channel TINYINT(1) NOT NULL DEFAULT 0,
        bonus TINYINT(1) NOT NULL DEFAULT 1,
        unity_id INT NULL,
        is_banned TINYINT(1) NOT NULL DEFAULT 0,
        balance_seq BIGINT NOT NULL DEFAULT 0,
        data_version BIGINT NOT NULL DEFAULT 0,
        bonus_notify_msg_id BIGINT NULL DEFAULT NULL,
        INDEX (unity_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    f"""CREATE TABLE IF NOT EXISTS {ZOOPARK_ANIMALS_TABLE} (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        animal_info_id INT NOT NULL,
        quantity INT NOT NULL DEFAULT 0,
        income BIGINT NOT NULL DEFAULT 0,
        price BIGINT NOT NULL DEFAULT 0,
        UNIQUE KEY uq_user_animal (user_id, animal_info_id),
        INDEX (user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    f"""CREATE TABLE IF NOT EXISTS {ZOOPARK_AVIARIES_TABLE} (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        aviary_info_id INT NOT NULL,
        price BIGINT NOT NULL DEFAULT 0,
        size INT NOT NULL DEFAULT 0,
        quantity INT NOT NULL DEFAULT 0,
        buy_count INT NOT NULL DEFAULT 0,
        UNIQUE KEY uq_user_aviary (user_id, aviary_info_id),
        INDEX (user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    f"""CREATE TABLE IF NOT EXISTS {ZOOPARK_ITEMS_TABLE} (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        emoji VARCHAR(20) NOT NULL,
        name VARCHAR(64) NOT NULL,
        lvl INT NOT NULL DEFAULT 1,
        properties LONGTEXT NULL,
        rarity VARCHAR(20) NOT NULL DEFAULT 'common',
        is_active TINYINT(1) NOT NULL DEFAULT 0,
        INDEX (user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    f"""CREATE TABLE IF NOT EXISTS {ZOOPARK_UNITY_TABLE} (
        idpk INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        id BIGINT NOT NULL UNIQUE,
        name VARCHAR(64) NOT NULL UNIQUE,
        level INT NOT NULL DEFAULT 1,
        owner_id INT NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS animals_info (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(64) NOT NULL,
        price BIGINT NOT NULL,
        income BIGINT NOT NULL,
        UNIQUE KEY uq_animals_info_name (name)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS aviaries_info (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(64) NOT NULL,
        price BIGINT NOT NULL,
        size INT NOT NULL,
        UNIQUE KEY uq_aviaries_info_name (name)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    f"""CREATE TABLE IF NOT EXISTS {ZOOPARK_EXTRA_TABLE} (
        user_id INT NOT NULL UNIQUE,
        balance_seq BIGINT NOT NULL DEFAULT 0,
        data_version BIGINT NOT NULL DEFAULT 0,
        profile_emoji VARCHAR(20) DEFAULT NULL,
        packs_today INT NOT NULL DEFAULT 0,
        packs_today_date DATE NULL,
        last_income_at DATETIME NULL,
        PRIMARY KEY (user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    f"""CREATE TABLE IF NOT EXISTS {ZOOPARK_SICK_EVENTS_TABLE} (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        animal_id VARCHAR(30) NOT NULL,
        since DATETIME NOT NULL,
        penalty_rub_per_min BIGINT NOT NULL DEFAULT 500,
        INDEX (user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    f"""CREATE TABLE IF NOT EXISTS {ZOOPARK_MP_GAMES_TABLE} (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        game_type VARCHAR(20) NOT NULL,
        bet_rub BIGINT NOT NULL,
        creator_id INT NOT NULL,
        opponent_id INT DEFAULT NULL,
        status ENUM('open','playing','finished') NOT NULL DEFAULT 'open',
        creator_score INT DEFAULT NULL,
        opponent_score INT DEFAULT NULL,
        winner_id INT DEFAULT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX (status),
        INDEX (creator_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    f"""CREATE TABLE IF NOT EXISTS {ZOOPARK_SOLO_STATS_TABLE} (
        user_id INT NOT NULL PRIMARY KEY,
        games_played INT NOT NULL DEFAULT 0,
        wins INT NOT NULL DEFAULT 0,
        losses INT NOT NULL DEFAULT 0,
        total_won BIGINT NOT NULL DEFAULT 0,
        total_lost BIGINT NOT NULL DEFAULT 0
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    f"""CREATE TABLE IF NOT EXISTS {ZOOPARK_COCKTAIL_SESSIONS_TABLE} (
        user_id INT NOT NULL PRIMARY KEY,
        secret TEXT NOT NULL,
        attempts INT NOT NULL DEFAULT 0,
        won TINYINT(1) NOT NULL DEFAULT 0,
        started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    f"""CREATE TABLE IF NOT EXISTS {ZOOPARK_TRANSFER_LINKS_TABLE} (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        link_key VARCHAR(32) NOT NULL UNIQUE,
        creator_id INT NOT NULL,
        total_amount BIGINT NOT NULL,
        rub_per_claim BIGINT NOT NULL,
        max_claims INT NOT NULL,
        claims INT NOT NULL DEFAULT 0,
        active TINYINT(1) NOT NULL DEFAULT 1,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX (creator_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    f"""CREATE TABLE IF NOT EXISTS {ZOOPARK_MERCHANTS_TABLE} (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        animal_info_id INT NOT NULL,
        name VARCHAR(64) NOT NULL,
        discount INT NOT NULL DEFAULT 0,
        price_with_discount BIGINT NOT NULL DEFAULT 0,
        quantity_animals INT NOT NULL DEFAULT 1,
        price BIGINT NOT NULL DEFAULT 0,
        first_offer_bought TINYINT(1) NOT NULL DEFAULT 0,
        INDEX (user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    f"""CREATE TABLE IF NOT EXISTS {ZOOPARK_PACK_ANIMALS_TABLE} (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        survival ENUM('low','medium','high') NOT NULL,
        reproduction ENUM('low','medium','high') NOT NULL,
        appearance ENUM('low','medium','high') NOT NULL,
        size_trait ENUM('low','medium','high') NOT NULL,
        habitat ENUM('desert','mountains','forest','fields','antarctica') NOT NULL,
        is_alive TINYINT(1) NOT NULL DEFAULT 1,
        acquired_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        dies_at DATETIME NULL,
        locality_id INT NULL,
        last_bred_date DATE NULL,
        in_expedition INT NULL,
        INDEX (user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    f"""CREATE TABLE IF NOT EXISTS {ZOOPARK_LOCALITIES_TABLE} (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        habitat ENUM('desert','mountains','forest','fields','antarctica') NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX (user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    f"""CREATE TABLE IF NOT EXISTS {ZOOPARK_EXPEDITIONS_TABLE} (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        locality_habitat ENUM('desert','mountains','forest','fields','antarctica') NOT NULL,
        started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        ends_at DATETIME NOT NULL,
        status ENUM('active','finished') NOT NULL DEFAULT 'active',
        result_json TEXT NULL,
        result_seen TINYINT(1) NOT NULL DEFAULT 0,
        INDEX (user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    f"""CREATE TABLE IF NOT EXISTS {ZOOPARK_EXPEDITION_ANIMALS_TABLE} (
        expedition_id INT NOT NULL,
        animal_id INT NOT NULL,
        PRIMARY KEY (expedition_id, animal_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    f"""CREATE TABLE IF NOT EXISTS {ZOOPARK_REFERRALS_TABLE} (
        user_id INT NOT NULL,
        referral_id INT NOT NULL,
        UNIQUE KEY uq_referral_pair (user_id, referral_id),
        INDEX (user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
)

MISSING_COLUMN_SQL: Sequence[str] = (
    f"ALTER TABLE {ZOOPARK_EXTRA_TABLE} ADD COLUMN packs_today INT NOT NULL DEFAULT 0",
    f"ALTER TABLE {ZOOPARK_EXTRA_TABLE} ADD COLUMN packs_today_date DATE NULL",
    f"ALTER TABLE {ZOOPARK_PACK_ANIMALS_TABLE} ADD COLUMN dies_at DATETIME NULL",
    f"ALTER TABLE {ZOOPARK_PACK_ANIMALS_TABLE} ADD COLUMN locality_id INT NULL",
    f"ALTER TABLE {ZOOPARK_PACK_ANIMALS_TABLE} ADD COLUMN last_bred_date DATE NULL",
    f"ALTER TABLE {ZOOPARK_PACK_ANIMALS_TABLE} ADD COLUMN in_expedition INT NULL",
    f"ALTER TABLE {ZOOPARK_EXTRA_TABLE} ADD COLUMN last_income_at DATETIME NULL",
)

COPY_COMPAT_TABLES: Sequence[tuple[str, str, tuple[str, ...], tuple[str, ...]]] = (
    (
        "users",
        ZOOPARK_USERS_TABLE,
        ("id", "id_user", "nickname", "date_reg", "paw_coins", "rub", "usd", "sub_on_chat", "sub_on_channel", "bonus"),
        ("unity_id", "is_banned", "balance_seq", "data_version", "bonus_notify_msg_id"),
    ),
    (
        "animals",
        ZOOPARK_ANIMALS_TABLE,
        ("id", "user_id", "animal_info_id", "quantity", "income", "price"),
        (),
    ),
    (
        "aviaries",
        ZOOPARK_AVIARIES_TABLE,
        ("id", "user_id", "aviary_info_id", "price", "size", "quantity", "buy_count"),
        (),
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
        "webapp_extra",
        ZOOPARK_EXTRA_TABLE,
        ("user_id", "balance_seq", "data_version"),
        ("profile_emoji", "packs_today", "packs_today_date", "last_income_at"),
    ),
    (
        "sick_events",
        ZOOPARK_SICK_EVENTS_TABLE,
        ("id", "user_id", "animal_id", "since", "penalty_rub_per_min"),
        (),
    ),
    (
        "merchants",
        ZOOPARK_MERCHANTS_TABLE,
        ("id", "user_id", "animal_info_id", "name", "discount", "price_with_discount", "quantity_animals", "price", "first_offer_bought"),
        (),
    ),
    (
        "pack_animals",
        ZOOPARK_PACK_ANIMALS_TABLE,
        ("id", "user_id", "survival", "reproduction", "appearance", "size_trait", "habitat", "is_alive", "acquired_at"),
        ("dies_at", "locality_id", "last_bred_date", "in_expedition"),
    ),
    (
        "player_localities",
        ZOOPARK_LOCALITIES_TABLE,
        ("id", "user_id", "habitat", "created_at"),
        (),
    ),
    (
        "expeditions",
        ZOOPARK_EXPEDITIONS_TABLE,
        ("id", "user_id", "locality_habitat", "started_at", "ends_at", "status"),
        ("result_json", "result_seen"),
    ),
    (
        "expedition_animals",
        ZOOPARK_EXPEDITION_ANIMALS_TABLE,
        ("expedition_id", "animal_id"),
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


def _table_exists(cur, table: str) -> bool:
    cur.execute(
        "SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME=%s LIMIT 1",
        (table,),
    )
    return cur.fetchone() is not None


def _available_columns(cur, table: str) -> set[str]:
    cur.execute(
        "SELECT COLUMN_NAME FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME=%s",
        (table,),
    )
    return {str(row["COLUMN_NAME"]) for row in cur.fetchall()}


def _column_data_type(cur, table: str, column: str) -> str | None:
    cur.execute(
        "SELECT DATA_TYPE FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME=%s AND COLUMN_NAME=%s LIMIT 1",
        (table, column),
    )
    row = cur.fetchone()
    return None if row is None else str(row["DATA_TYPE"]).lower()


def _ensure_bigint_column(cur, table: str, column: str) -> None:
    if not _table_exists(cur, table):
        return
    if _column_data_type(cur, table, column) == "bigint":
        return
    cur.execute(f"ALTER TABLE {table} MODIFY COLUMN {column} BIGINT NOT NULL DEFAULT 0")


def _copy_compat_table(cur, source_table: str, target_table: str, required: Sequence[str], optional: Sequence[str]) -> None:
    if source_table == target_table or not _table_exists(cur, source_table) or not _table_exists(cur, target_table):
        return

    target_columns = _available_columns(cur, target_table)
    source_columns = _available_columns(cur, source_table)
    if not set(required).issubset(target_columns) or not set(required).issubset(source_columns):
        return

    cur.execute(f"SELECT COUNT(*) AS cnt FROM {target_table}")
    if int((cur.fetchone() or {}).get("cnt") or 0) > 0:
        return

    columns = [column for column in [*required, *optional] if column in target_columns and column in source_columns]
    column_sql = ", ".join(columns)
    cur.execute(f"INSERT INTO {target_table} ({column_sql}) SELECT {column_sql} FROM {source_table}")


def seed_catalogue(cur) -> None:
    cur.execute("SELECT COUNT(*) AS cnt FROM animals_info")
    if cur.fetchone()["cnt"] < len(ANIMALS):
        cur.execute("DELETE FROM animals_info")
        for index, animal in enumerate(ANIMALS, start=1):
            cur.execute(
                "INSERT INTO animals_info (id, name, price, income) VALUES (%s,%s,%s,%s)",
                (index, animal["id"], animal["price"], animal["income"]),
            )

    cur.execute("SELECT COUNT(*) AS cnt FROM aviaries_info")
    if cur.fetchone()["cnt"] < len(AVIARIES):
        cur.execute("DELETE FROM aviaries_info")
        for index, aviary in enumerate(AVIARIES, start=1):
            cur.execute(
                "INSERT INTO aviaries_info (id, name, price, size) VALUES (%s,%s,%s,%s)",
                (index, aviary["id"], aviary["price"], aviary["seats"]),
            )


def init_schema() -> None:
    db = get_db()
    try:
        with db.cursor() as cur:
            for sql in CREATE_TABLES_SQL:
                cur.execute(sql)
            _ensure_bigint_column(cur, ZOOPARK_USERS_TABLE, "balance_seq")
            _ensure_bigint_column(cur, ZOOPARK_EXTRA_TABLE, "balance_seq")
            for sql in MISSING_COLUMN_SQL:
                try:
                    cur.execute(sql)
                except Exception:
                    pass
            for source_table, target_table, required, optional in COPY_COMPAT_TABLES:
                _copy_compat_table(cur, source_table, target_table, required, optional)
            seed_catalogue(cur)
        db.commit()
    finally:
        db.close()
