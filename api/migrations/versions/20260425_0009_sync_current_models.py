from __future__ import annotations

from types import SimpleNamespace

from sqlalchemy import text

try:
    from alembic import op
except Exception:  # pragma: no cover - keeps helper unit tests importable without Alembic.
    op = SimpleNamespace(get_bind=lambda: None)


revision = "20260425_0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def _conn():
    return op.get_bind()


def _execute(sql: str) -> None:
    _conn().execute(text(sql))


def _table_exists(table: str) -> bool:
    result = _conn().execute(
        text("SELECT 1 FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME=:table LIMIT 1"),
        {"table": table},
    )
    return result.fetchone() is not None


def _column_exists(table: str, column: str) -> bool:
    result = _conn().execute(
        text(
            "SELECT 1 FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME=:table AND COLUMN_NAME=:column LIMIT 1"
        ),
        {"table": table, "column": column},
    )
    return result.fetchone() is not None


def _index_exists(table: str, index: str) -> bool:
    result = _conn().execute(
        text(
            "SELECT 1 FROM information_schema.STATISTICS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME=:table AND INDEX_NAME=:index LIMIT 1"
        ),
        {"table": table, "index": index},
    )
    return result.fetchone() is not None


def _constraint_exists(table: str, name: str) -> bool:
    result = _conn().execute(
        text(
            "SELECT 1 FROM information_schema.TABLE_CONSTRAINTS "
            "WHERE CONSTRAINT_SCHEMA = DATABASE() AND TABLE_NAME=:table AND CONSTRAINT_NAME=:name LIMIT 1"
        ),
        {"table": table, "name": name},
    )
    return result.fetchone() is not None


def _add_column_if_missing(table: str, column: str, definition: str) -> None:
    if _table_exists(table) and not _column_exists(table, column):
        _execute(f"ALTER TABLE `{table}` ADD COLUMN {definition}")


def _add_index_if_missing(table: str, index: str, statement: str) -> None:
    if _table_exists(table) and not _index_exists(table, index):
        _execute(statement)


def _create_tables() -> None:
    _execute(
        """
        CREATE TABLE IF NOT EXISTS `animals_info` (
            `id` INT NOT NULL AUTO_INCREMENT,
            `name` VARCHAR(64) NOT NULL,
            `price` BIGINT NOT NULL,
            `income` BIGINT NOT NULL,
            PRIMARY KEY (`id`),
            UNIQUE KEY `uq_animals_info_name` (`name`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    _execute(
        """
        CREATE TABLE IF NOT EXISTS `zoopark_users` (
            `id` INT NOT NULL AUTO_INCREMENT,
            `id_user` BIGINT NOT NULL,
            `nickname` VARCHAR(64) NOT NULL,
            `date_reg` DATETIME NOT NULL,
            `paw_coins` BIGINT NOT NULL DEFAULT 0,
            `rub` BIGINT NOT NULL DEFAULT 0,
            `usd` BIGINT NOT NULL DEFAULT 0,
            `sub_on_chat` SMALLINT NOT NULL DEFAULT 0,
            `sub_on_channel` SMALLINT NOT NULL DEFAULT 0,
            `bonus` SMALLINT NOT NULL DEFAULT 1,
            `unity_id` INT NULL,
            `is_banned` SMALLINT NOT NULL DEFAULT 0,
            `balance_seq` BIGINT NOT NULL DEFAULT 0,
            `data_version` BIGINT NOT NULL DEFAULT 0,
            `bonus_notify_msg_id` BIGINT NULL,
            `profile_emoji` VARCHAR(20) NULL,
            `last_income_at` DATETIME NULL,
            PRIMARY KEY (`id`),
            UNIQUE KEY `id_user` (`id_user`),
            KEY `idx_unity_id` (`unity_id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    _execute(
        """
        CREATE TABLE IF NOT EXISTS `zoopark_seasons` (
            `id` INT NOT NULL AUTO_INCREMENT,
            `starts_at` DATETIME NOT NULL,
            `ends_at` DATETIME NOT NULL,
            `status` VARCHAR(16) NOT NULL DEFAULT 'active',
            `created_at` DATETIME NOT NULL,
            PRIMARY KEY (`id`),
            KEY `idx_status` (`status`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    _execute(
        """
        CREATE TABLE IF NOT EXISTS `zoopark_player_seasons` (
            `user_id` INT NOT NULL,
            `season_id` INT NOT NULL,
            `joined_at` DATETIME NOT NULL,
            PRIMARY KEY (`user_id`, `season_id`),
            KEY `idx_season_id` (`season_id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    _execute(
        """
        CREATE TABLE IF NOT EXISTS `zoopark_items` (
            `id` INT NOT NULL AUTO_INCREMENT,
            `user_id` INT NOT NULL,
            `emoji` VARCHAR(20) NOT NULL,
            `name` VARCHAR(64) NOT NULL,
            `lvl` INT NOT NULL DEFAULT 1,
            `properties` TEXT NULL,
            `rarity` VARCHAR(20) NOT NULL DEFAULT 'common',
            `is_active` SMALLINT NOT NULL DEFAULT 0,
            PRIMARY KEY (`id`),
            KEY `idx_user_id` (`user_id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    _execute(
        """
        CREATE TABLE IF NOT EXISTS `zoopark_forge_sets` (
            `id` INT NOT NULL AUTO_INCREMENT,
            `user_id` INT NOT NULL,
            `set_key` VARCHAR(32) NOT NULL,
            `name` VARCHAR(32) NOT NULL,
            `icon` VARCHAR(20) NOT NULL DEFAULT '⚒️',
            `created_at` DATETIME NOT NULL,
            PRIMARY KEY (`id`),
            UNIQUE KEY `uq_user_forge_set_key` (`user_id`, `set_key`),
            KEY `idx_user_id` (`user_id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    _execute(
        """
        CREATE TABLE IF NOT EXISTS `zoopark_forge_set_items` (
            `set_id` INT NOT NULL,
            `item_id` INT NOT NULL,
            `position` INT NOT NULL DEFAULT 0,
            PRIMARY KEY (`set_id`, `item_id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    _execute(
        """
        CREATE TABLE IF NOT EXISTS `zoopark_unity` (
            `idpk` INT NOT NULL AUTO_INCREMENT,
            `id` BIGINT NOT NULL,
            `name` VARCHAR(64) NOT NULL,
            `level` INT NOT NULL DEFAULT 1,
            `owner_id` INT NOT NULL,
            PRIMARY KEY (`idpk`),
            UNIQUE KEY `id` (`id`),
            UNIQUE KEY `name` (`name`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    _execute(
        """
        CREATE TABLE IF NOT EXISTS `zoopark_sick_events` (
            `id` INT NOT NULL AUTO_INCREMENT,
            `user_id` INT NOT NULL,
            `animal_id` INT NOT NULL,
            `since` DATETIME NOT NULL,
            `penalty_rub_per_min` BIGINT NOT NULL DEFAULT 500,
            PRIMARY KEY (`id`),
            KEY `idx_user_id` (`user_id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    _execute(
        """
        CREATE TABLE IF NOT EXISTS `zoopark_mp_games` (
            `id` INT NOT NULL AUTO_INCREMENT,
            `game_type` VARCHAR(20) NOT NULL,
            `bet_rub` BIGINT NOT NULL,
            `creator_id` INT NOT NULL,
            `opponent_id` INT NULL,
            `status` VARCHAR(10) NOT NULL DEFAULT 'open',
            `creator_score` INT NULL,
            `opponent_score` INT NULL,
            `winner_id` INT NULL,
            `created_at` DATETIME NOT NULL,
            PRIMARY KEY (`id`),
            KEY `idx_status` (`status`),
            KEY `idx_creator_id` (`creator_id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    _execute(
        """
        CREATE TABLE IF NOT EXISTS `zoopark_solo_stats` (
            `user_id` INT NOT NULL,
            `games_played` INT NOT NULL DEFAULT 0,
            `wins` INT NOT NULL DEFAULT 0,
            `losses` INT NOT NULL DEFAULT 0,
            `total_won` BIGINT NOT NULL DEFAULT 0,
            `total_lost` BIGINT NOT NULL DEFAULT 0,
            PRIMARY KEY (`user_id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    _execute(
        """
        CREATE TABLE IF NOT EXISTS `zoopark_cocktail_sessions` (
            `user_id` INT NOT NULL,
            `secret` TEXT NOT NULL,
            `attempts` INT NOT NULL DEFAULT 0,
            `won` SMALLINT NOT NULL DEFAULT 0,
            `started_at` DATETIME NOT NULL,
            PRIMARY KEY (`user_id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    _execute(
        """
        CREATE TABLE IF NOT EXISTS `zoopark_transfer_links` (
            `id` INT NOT NULL AUTO_INCREMENT,
            `link_key` VARCHAR(32) NOT NULL,
            `creator_id` INT NOT NULL,
            `total_amount` BIGINT NOT NULL,
            `rub_per_claim` BIGINT NOT NULL,
            `max_claims` INT NOT NULL,
            `claims` INT NOT NULL DEFAULT 0,
            `active` SMALLINT NOT NULL DEFAULT 1,
            `created_at` DATETIME NOT NULL,
            PRIMARY KEY (`id`),
            UNIQUE KEY `link_key` (`link_key`),
            KEY `idx_creator_id` (`creator_id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    _execute(
        """
        CREATE TABLE IF NOT EXISTS `zoopark_merchant_offers` (
            `id` INT NOT NULL AUTO_INCREMENT,
            `user_id` INT NOT NULL,
            `season_id` INT NOT NULL,
            `animal_info_id` INT NOT NULL,
            `survival` VARCHAR(10) NOT NULL,
            `reproduction` VARCHAR(10) NOT NULL,
            `appearance` VARCHAR(10) NOT NULL,
            `size_trait` VARCHAR(10) NOT NULL,
            `habitat` VARCHAR(15) NOT NULL,
            `discount` INT NOT NULL DEFAULT 0,
            `price` BIGINT NOT NULL DEFAULT 0,
            `price_with_discount` BIGINT NOT NULL DEFAULT 0,
            `bought` SMALLINT NOT NULL DEFAULT 0,
            `created_at` DATETIME NOT NULL,
            `expires_at` DATETIME NOT NULL,
            PRIMARY KEY (`id`),
            KEY `idx_user_id` (`user_id`),
            KEY `idx_season_id` (`season_id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    _execute(
        """
        CREATE TABLE IF NOT EXISTS `zoopark_pack_animals` (
            `id` INT NOT NULL AUTO_INCREMENT,
            `user_id` INT NOT NULL,
            `season_id` INT NOT NULL,
            `animal_info_id` INT NOT NULL,
            `survival` VARCHAR(10) NOT NULL,
            `reproduction` VARCHAR(10) NOT NULL,
            `appearance` VARCHAR(10) NOT NULL,
            `size_trait` VARCHAR(10) NOT NULL,
            `habitat` VARCHAR(15) NOT NULL,
            `source` VARCHAR(20) NOT NULL DEFAULT 'pack',
            `parent_1_id` INT NULL,
            `parent_2_id` INT NULL,
            `is_alive` SMALLINT NOT NULL DEFAULT 1,
            `acquired_at` DATETIME NOT NULL,
            `dies_at` DATETIME NULL,
            `locality_id` INT NULL,
            `last_bred_date` DATE NULL,
            PRIMARY KEY (`id`),
            KEY `idx_user_id` (`user_id`),
            KEY `idx_season_id` (`season_id`),
            KEY `idx_locality_id` (`locality_id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    _execute(
        """
        CREATE TABLE IF NOT EXISTS `zoopark_pack_openings` (
            `id` INT NOT NULL AUTO_INCREMENT,
            `user_id` INT NOT NULL,
            `season_id` INT NOT NULL,
            `animal_id` INT NOT NULL,
            `opened_at` DATETIME NOT NULL,
            `price_paid` BIGINT NOT NULL DEFAULT 0,
            `is_free` BOOLEAN NOT NULL DEFAULT FALSE,
            PRIMARY KEY (`id`),
            KEY `idx_user_season_opened` (`user_id`, `season_id`, `opened_at`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    _execute(
        """
        CREATE TABLE IF NOT EXISTS `zoopark_player_localities` (
            `id` INT NOT NULL AUTO_INCREMENT,
            `user_id` INT NOT NULL,
            `season_id` INT NOT NULL,
            `habitat` VARCHAR(15) NOT NULL,
            `created_at` DATETIME NOT NULL,
            PRIMARY KEY (`id`),
            UNIQUE KEY `uq_user_season_habitat` (`user_id`, `season_id`, `habitat`),
            KEY `idx_user_id` (`user_id`),
            KEY `idx_season_id` (`season_id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    _execute(
        """
        CREATE TABLE IF NOT EXISTS `zoopark_expeditions` (
            `id` INT NOT NULL AUTO_INCREMENT,
            `user_id` INT NOT NULL,
            `season_id` INT NOT NULL,
            `locality_id` INT NOT NULL,
            `started_at` DATETIME NOT NULL,
            `ends_at` DATETIME NOT NULL,
            `status` VARCHAR(10) NOT NULL DEFAULT 'active',
            `result_json` TEXT NULL,
            `result_seen` SMALLINT NOT NULL DEFAULT 0,
            PRIMARY KEY (`id`),
            KEY `idx_user_id` (`user_id`),
            KEY `idx_season_id` (`season_id`),
            KEY `idx_status` (`status`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    _execute(
        """
        CREATE TABLE IF NOT EXISTS `zoopark_expedition_animals` (
            `expedition_id` INT NOT NULL,
            `animal_id` INT NOT NULL,
            PRIMARY KEY (`expedition_id`, `animal_id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    _execute(
        """
        CREATE TABLE IF NOT EXISTS `zoopark_breeding_events` (
            `id` INT NOT NULL AUTO_INCREMENT,
            `user_id` INT NOT NULL,
            `season_id` INT NOT NULL,
            `parent_1_id` INT NOT NULL,
            `parent_2_id` INT NOT NULL,
            `child_id` INT NULL,
            `success_rate` INT NOT NULL,
            `success` SMALLINT NOT NULL DEFAULT 0,
            `created_at` DATETIME NOT NULL,
            PRIMARY KEY (`id`),
            KEY `idx_user_season_created` (`user_id`, `season_id`, `created_at`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    _execute(
        """
        CREATE TABLE IF NOT EXISTS `zoopark_referrals` (
            `user_id` INT NOT NULL,
            `referral_id` INT NOT NULL,
            PRIMARY KEY (`user_id`, `referral_id`),
            UNIQUE KEY `uq_referral_pair` (`user_id`, `referral_id`),
            KEY `idx_user_id` (`user_id`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )
    _execute(
        """
        CREATE TABLE IF NOT EXISTS `zoopark_bootstrap_meta` (
            `target_table` VARCHAR(64) NOT NULL,
            `copied_at` DATETIME NOT NULL,
            PRIMARY KEY (`target_table`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
    )


def _add_missing_columns() -> None:
    columns: dict[str, list[tuple[str, str]]] = {
        "zoopark_users": [
            ("paw_coins", "`paw_coins` BIGINT NOT NULL DEFAULT 0"),
            ("rub", "`rub` BIGINT NOT NULL DEFAULT 0"),
            ("usd", "`usd` BIGINT NOT NULL DEFAULT 0"),
            ("sub_on_chat", "`sub_on_chat` SMALLINT NOT NULL DEFAULT 0"),
            ("sub_on_channel", "`sub_on_channel` SMALLINT NOT NULL DEFAULT 0"),
            ("bonus", "`bonus` SMALLINT NOT NULL DEFAULT 1"),
            ("unity_id", "`unity_id` INT NULL"),
            ("is_banned", "`is_banned` SMALLINT NOT NULL DEFAULT 0"),
            ("balance_seq", "`balance_seq` BIGINT NOT NULL DEFAULT 0"),
            ("data_version", "`data_version` BIGINT NOT NULL DEFAULT 0"),
            ("bonus_notify_msg_id", "`bonus_notify_msg_id` BIGINT NULL"),
            ("profile_emoji", "`profile_emoji` VARCHAR(20) NULL"),
            ("last_income_at", "`last_income_at` DATETIME NULL"),
        ],
        "zoopark_items": [
            ("properties", "`properties` TEXT NULL"),
            ("rarity", "`rarity` VARCHAR(20) NOT NULL DEFAULT 'common'"),
            ("is_active", "`is_active` SMALLINT NOT NULL DEFAULT 0"),
        ],
        "zoopark_forge_sets": [
            ("set_key", "`set_key` VARCHAR(32) NOT NULL"),
            ("name", "`name` VARCHAR(32) NOT NULL DEFAULT 'Сет'"),
            ("icon", "`icon` VARCHAR(20) NOT NULL DEFAULT '⚒️'"),
            ("created_at", "`created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP"),
        ],
        "zoopark_forge_set_items": [("position", "`position` INT NOT NULL DEFAULT 0")],
        "zoopark_pack_animals": [
            ("source", "`source` VARCHAR(20) NOT NULL DEFAULT 'pack'"),
            ("parent_1_id", "`parent_1_id` INT NULL"),
            ("parent_2_id", "`parent_2_id` INT NULL"),
            ("is_alive", "`is_alive` SMALLINT NOT NULL DEFAULT 1"),
            ("dies_at", "`dies_at` DATETIME NULL"),
            ("locality_id", "`locality_id` INT NULL"),
            ("last_bred_date", "`last_bred_date` DATE NULL"),
        ],
        "zoopark_expeditions": [
            ("result_json", "`result_json` TEXT NULL"),
            ("result_seen", "`result_seen` SMALLINT NOT NULL DEFAULT 0"),
        ],
        "zoopark_transfer_links": [
            ("claims", "`claims` INT NOT NULL DEFAULT 0"),
            ("active", "`active` SMALLINT NOT NULL DEFAULT 1"),
        ],
    }
    for table, table_columns in columns.items():
        for column, definition in table_columns:
            _add_column_if_missing(table, column, definition)


def _add_missing_indexes() -> None:
    indexes = [
        ("zoopark_users", "idx_unity_id", "CREATE INDEX `idx_unity_id` ON `zoopark_users` (`unity_id`)"),
        ("zoopark_seasons", "idx_status", "CREATE INDEX `idx_status` ON `zoopark_seasons` (`status`)"),
        ("zoopark_player_seasons", "idx_season_id", "CREATE INDEX `idx_season_id` ON `zoopark_player_seasons` (`season_id`)"),
        ("zoopark_items", "idx_user_id", "CREATE INDEX `idx_user_id` ON `zoopark_items` (`user_id`)"),
        ("zoopark_forge_sets", "idx_user_id", "CREATE INDEX `idx_user_id` ON `zoopark_forge_sets` (`user_id`)"),
        ("zoopark_sick_events", "idx_user_id", "CREATE INDEX `idx_user_id` ON `zoopark_sick_events` (`user_id`)"),
        ("zoopark_mp_games", "idx_status", "CREATE INDEX `idx_status` ON `zoopark_mp_games` (`status`)"),
        ("zoopark_mp_games", "idx_creator_id", "CREATE INDEX `idx_creator_id` ON `zoopark_mp_games` (`creator_id`)"),
        ("zoopark_transfer_links", "idx_creator_id", "CREATE INDEX `idx_creator_id` ON `zoopark_transfer_links` (`creator_id`)"),
        ("zoopark_merchant_offers", "idx_user_id", "CREATE INDEX `idx_user_id` ON `zoopark_merchant_offers` (`user_id`)"),
        ("zoopark_merchant_offers", "idx_season_id", "CREATE INDEX `idx_season_id` ON `zoopark_merchant_offers` (`season_id`)"),
        ("zoopark_pack_animals", "idx_user_id", "CREATE INDEX `idx_user_id` ON `zoopark_pack_animals` (`user_id`)"),
        ("zoopark_pack_animals", "idx_season_id", "CREATE INDEX `idx_season_id` ON `zoopark_pack_animals` (`season_id`)"),
        ("zoopark_pack_animals", "idx_locality_id", "CREATE INDEX `idx_locality_id` ON `zoopark_pack_animals` (`locality_id`)"),
        (
            "zoopark_pack_openings",
            "idx_user_season_opened",
            "CREATE INDEX `idx_user_season_opened` ON `zoopark_pack_openings` (`user_id`, `season_id`, `opened_at`)",
        ),
        ("zoopark_player_localities", "idx_user_id", "CREATE INDEX `idx_user_id` ON `zoopark_player_localities` (`user_id`)"),
        ("zoopark_player_localities", "idx_season_id", "CREATE INDEX `idx_season_id` ON `zoopark_player_localities` (`season_id`)"),
        ("zoopark_expeditions", "idx_user_id", "CREATE INDEX `idx_user_id` ON `zoopark_expeditions` (`user_id`)"),
        ("zoopark_expeditions", "idx_season_id", "CREATE INDEX `idx_season_id` ON `zoopark_expeditions` (`season_id`)"),
        ("zoopark_expeditions", "idx_status", "CREATE INDEX `idx_status` ON `zoopark_expeditions` (`status`)"),
        (
            "zoopark_breeding_events",
            "idx_user_season_created",
            "CREATE INDEX `idx_user_season_created` ON `zoopark_breeding_events` (`user_id`, `season_id`, `created_at`)",
        ),
        ("zoopark_referrals", "idx_user_id", "CREATE INDEX `idx_user_id` ON `zoopark_referrals` (`user_id`)"),
    ]
    for table, index, statement in indexes:
        _add_index_if_missing(table, index, statement)

    if _table_exists("zoopark_transfer_links") and not _index_exists("zoopark_transfer_links", "link_key"):
        _execute("CREATE UNIQUE INDEX `link_key` ON `zoopark_transfer_links` (`link_key`)")
    if (
        _table_exists("zoopark_forge_sets")
        and not _constraint_exists("zoopark_forge_sets", "uq_user_forge_set_key")
        and not _index_exists("zoopark_forge_sets", "uq_user_forge_set_key")
    ):
        _execute("CREATE UNIQUE INDEX `uq_user_forge_set_key` ON `zoopark_forge_sets` (`user_id`, `set_key`)")
    if (
        _table_exists("zoopark_player_localities")
        and not _constraint_exists("zoopark_player_localities", "uq_user_season_habitat")
        and not _index_exists("zoopark_player_localities", "uq_user_season_habitat")
    ):
        _execute("CREATE UNIQUE INDEX `uq_user_season_habitat` ON `zoopark_player_localities` (`user_id`, `season_id`, `habitat`)")


def _seed_animals_info() -> None:
    try:
        from api.app.zoopark.catalog import ANIMALS
    except Exception:
        return

    if not _table_exists("animals_info"):
        return

    for index, animal in enumerate(ANIMALS, start=1):
        _conn().execute(
            text(
                "INSERT INTO `animals_info` (`id`, `name`, `price`, `income`) "
                "VALUES (:id, :name, :price, :income) "
                "ON DUPLICATE KEY UPDATE `name`=VALUES(`name`), `price`=VALUES(`price`), `income`=VALUES(`income`)"
            ),
            {"id": index, "name": animal["id"], "price": animal["price"], "income": animal["income"]},
        )


def upgrade() -> None:
    _create_tables()
    _add_missing_columns()
    _add_missing_indexes()
    _seed_animals_info()


def downgrade() -> None:
    # Destructive rollback is intentionally omitted: this migration is a server
    # schema sync that creates canonical tables and preserves production data.
    pass
