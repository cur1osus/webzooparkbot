"""Initial schema: all tables and columns from deploy.sh

Revision ID: 0001
Revises:
Create Date: 2026-04-07
"""
from typing import Sequence, Union
from alembic import op
from sqlalchemy import text

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _table_exists(conn, table: str) -> bool:
    row = conn.execute(
        text(
            "SELECT 1 FROM information_schema.TABLES "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table LIMIT 1"
        ),
        {"table": table},
    ).fetchone()
    return bool(row)


def _column_exists(conn, table: str, column: str) -> bool:
    row = conn.execute(
        text(
            "SELECT 1 FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table AND COLUMN_NAME = :column LIMIT 1"
        ),
        {"table": table, "column": column},
    ).fetchone()
    return bool(row)


def _columns_exist(conn, table: str, columns: list[str]) -> bool:
    return all(_column_exists(conn, table, column) for column in columns)


def _add_column_if_missing(table: str, column: str, definition: str) -> None:
    conn = op.get_bind()
    if not _table_exists(conn, table) or _column_exists(conn, table, column):
        return
    conn.execute(text(f"ALTER TABLE `{table}` ADD COLUMN {column} {definition}"))


def _index_exists(conn, table: str, index_name: str) -> bool:
    row = conn.execute(
        text(
            "SELECT 1 FROM information_schema.STATISTICS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :table AND INDEX_NAME = :index_name LIMIT 1"
        ),
        {"table": table, "index_name": index_name},
    ).fetchone()
    return bool(row)


def _add_index_if_missing(table: str, index_name: str, ddl: str) -> None:
    conn = op.get_bind()
    if not _table_exists(conn, table) or _index_exists(conn, table, index_name):
        return
    conn.execute(text(ddl))


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "mysql":
        return

    # ── users: дополнительные колонки ──────────────────────────────────────────
    _add_column_if_missing("users", "is_banned",          "TINYINT(1) DEFAULT 0")
    _add_column_if_missing("users", "balance_seq",        "INT DEFAULT 0")
    _add_column_if_missing("users", "data_version",       "BIGINT DEFAULT 0")
    _add_column_if_missing("users", "bonus_notify_msg_id","BIGINT NULL DEFAULT NULL")

    # ── webapp_extra ────────────────────────────────────────────────────────────
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS webapp_extra (
            idpk                        INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            idpk_user                   INT NOT NULL UNIQUE,
            bonus_last_claimed_ms       BIGINT DEFAULT 0,
            merchant_last_refresh_ms    BIGINT DEFAULT 0
        )
    """))
    _add_column_if_missing("webapp_extra", "solo_game_json",              "LONGTEXT NULL")
    _add_column_if_missing("webapp_extra", "solo_daily_rub_won",          "BIGINT DEFAULT 0")
    _add_column_if_missing("webapp_extra", "solo_daily_usd_won",          "BIGINT DEFAULT 0")
    _add_column_if_missing("webapp_extra", "solo_daily_reset_date",       "DATE NULL")
    _add_column_if_missing("webapp_extra", "stats_json",                  "LONGTEXT NULL")
    _add_column_if_missing("webapp_extra", "bonus_preview_json",          "LONGTEXT NULL")
    _add_column_if_missing("webapp_extra", "cocktail_game_json",          "LONGTEXT NULL")
    _add_column_if_missing("webapp_extra", "cocktail_daily_count",        "INT DEFAULT 0")
    _add_column_if_missing("webapp_extra", "cocktail_daily_date",         "DATE NULL")
    _add_column_if_missing("webapp_extra", "cocktail_day_attempts_json",  "LONGTEXT NULL")
    _add_column_if_missing("webapp_extra", "cocktail_day_date",           "DATE NULL")
    _add_column_if_missing("webapp_extra", "cocktail_day_won",            "TINYINT(1) DEFAULT 0")
    _add_column_if_missing("webapp_extra", "nickname_color",              "VARCHAR(20) NULL DEFAULT NULL")
    _add_column_if_missing("webapp_extra", "purchased_colors_json",       "TEXT NULL DEFAULT NULL")
    _add_column_if_missing("webapp_extra", "profile_animal_code_name",    "VARCHAR(64) NULL DEFAULT NULL")
    _add_column_if_missing("webapp_extra", "profile_animal_changed_at_ms","BIGINT DEFAULT 0")
    _add_column_if_missing("webapp_extra", "achievement_cosmetic_id",     "VARCHAR(50) NULL DEFAULT NULL")

    # ── item_logs ───────────────────────────────────────────────────────────────
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS item_logs (
            idpk        INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            id_user     BIGINT NOT NULL,
            action      VARCHAR(20) NOT NULL,
            id_item     VARCHAR(36) NOT NULL,
            item_name   VARCHAR(64),
            item_rarity VARCHAR(20),
            item_lvl    INT,
            extra       JSON,
            created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
            INDEX idx_user    (id_user),
            INDEX idx_created (created_at)
        )
    """))

    # ── aviaries: уникальный индекс + базовые данные ────────────────────────────
    if _columns_exist(conn, "aviaries", ["code_name"]):
        _add_index_if_missing(
            "aviaries", "uq_code_name",
            "ALTER TABLE aviaries ADD UNIQUE KEY uq_code_name (code_name)"
        )
    if _columns_exist(conn, "aviaries", ["code_name", "name", "size", "price"]):
        conn.execute(text("""
            INSERT IGNORE INTO aviaries (code_name, name, size, price) VALUES
                ('aviary_1', 'Вольер маленький', 5,  4000),
                ('aviary_2', 'Вольер средний',   12, 10000),
                ('aviary_3', 'Вольер большой',   20, 16000)
        """))

    # ── достижения ──────────────────────────────────────────────────────────────
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS user_achievements (
            id             INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
            user_idpk      INT NOT NULL,
            achievement_id VARCHAR(50) NOT NULL,
            unlocked_at    BIGINT NOT NULL,
            UNIQUE KEY uk_user_achievement (user_idpk, achievement_id),
            INDEX idx_user (user_idpk)
        )
    """))
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS user_achievement_progress (
            user_idpk          INT PRIMARY KEY,
            mp_wins_total      INT DEFAULT 0,
            top1_since         BIGINT NULL,
            top_prev_rank      INT NULL,
            top_gains_today    INT DEFAULT 0,
            last_top_gains_date DATE NULL
        )
    """))


def downgrade() -> None:
    # Намеренно пусто: откат начальной схемы не поддерживается
    pass
