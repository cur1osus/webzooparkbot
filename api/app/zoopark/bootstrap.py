from __future__ import annotations

from collections.abc import Sequence

from api.app.zoopark.catalog import ANIMALS, AVIARIES
from api.app.zoopark.runtime import get_db


CREATE_TABLES_SQL: Sequence[str] = (
    """CREATE TABLE IF NOT EXISTS webapp_extra (
        user_id INT NOT NULL UNIQUE,
        balance_seq INT NOT NULL DEFAULT 0,
        data_version BIGINT NOT NULL DEFAULT 0,
        profile_emoji VARCHAR(20) DEFAULT NULL,
        PRIMARY KEY (user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS sick_events (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        animal_id VARCHAR(30) NOT NULL,
        since DATETIME NOT NULL,
        penalty_rub_per_min BIGINT NOT NULL DEFAULT 500,
        INDEX (user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS mp_games_new (
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
    """CREATE TABLE IF NOT EXISTS solo_stats (
        user_id INT NOT NULL PRIMARY KEY,
        games_played INT NOT NULL DEFAULT 0,
        wins INT NOT NULL DEFAULT 0,
        losses INT NOT NULL DEFAULT 0,
        total_won BIGINT NOT NULL DEFAULT 0,
        total_lost BIGINT NOT NULL DEFAULT 0
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS cocktail_sessions (
        user_id INT NOT NULL PRIMARY KEY,
        secret TEXT NOT NULL,
        attempts INT NOT NULL DEFAULT 0,
        won TINYINT(1) NOT NULL DEFAULT 0,
        started_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS transfer_links (
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
    """CREATE TABLE IF NOT EXISTS pack_animals (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        survival ENUM('low','medium','high') NOT NULL,
        reproduction ENUM('low','medium','high') NOT NULL,
        appearance ENUM('low','medium','high') NOT NULL,
        size_trait ENUM('low','medium','high') NOT NULL,
        habitat ENUM('desert','mountains','forest','fields','antarctica') NOT NULL,
        is_alive TINYINT(1) NOT NULL DEFAULT 1,
        acquired_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX (user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS player_localities (
        id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
        user_id INT NOT NULL,
        habitat ENUM('desert','mountains','forest','fields','antarctica') NOT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX (user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
    """CREATE TABLE IF NOT EXISTS expeditions (
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
    """CREATE TABLE IF NOT EXISTS expedition_animals (
        expedition_id INT NOT NULL,
        animal_id INT NOT NULL,
        PRIMARY KEY (expedition_id, animal_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
)

MISSING_COLUMN_SQL: Sequence[str] = (
    "ALTER TABLE webapp_extra ADD COLUMN packs_today INT NOT NULL DEFAULT 0",
    "ALTER TABLE webapp_extra ADD COLUMN packs_today_date DATE NULL",
    "ALTER TABLE pack_animals ADD COLUMN dies_at DATETIME NULL",
    "ALTER TABLE pack_animals ADD COLUMN locality_id INT NULL",
    "ALTER TABLE pack_animals ADD COLUMN last_bred_date DATE NULL",
    "ALTER TABLE pack_animals ADD COLUMN in_expedition INT NULL",
    "ALTER TABLE webapp_extra ADD COLUMN last_income_at DATETIME NULL",
)


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
            seed_catalogue(cur)
            for sql in MISSING_COLUMN_SQL:
                try:
                    cur.execute(sql)
                except Exception:
                    pass
        db.commit()
    finally:
        db.close()
