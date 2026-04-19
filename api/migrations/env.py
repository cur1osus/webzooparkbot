import os
from logging.config import fileConfig

from sqlalchemy import create_engine, pool
from alembic import context

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Строка подключения — те же переменные, что и в main.py
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_USER = os.getenv("DB_USER", "zooparkbot")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME", "zooparkbot")

DB_URL = os.getenv("DB_URL") or f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Runtime schema is SQL-first and bootstrapped outside Alembic's ORM metadata.
target_metadata = None


def run_migrations_online() -> None:
    engine = create_engine(DB_URL, poolclass=pool.NullPool)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table="alembic_version_webapp",
        )
        with context.begin_transaction():
            context.run_migrations()


run_migrations_online()
