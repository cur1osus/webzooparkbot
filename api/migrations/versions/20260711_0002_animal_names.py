"""Add per-animal names.

Every animal gets an individual name so duplicate species can be told apart. New animals
are named at creation; this revision adds the column and backfills existing rows with a
random name from the same Renaissance-figure pool. The pool is inlined (not imported from
the app) so the migration stays self-contained.
"""

from __future__ import annotations

import random

import sqlalchemy as sa
from alembic import op

revision = "20260711_0002"
down_revision = "20260710_0001"
branch_labels = None
depends_on = None

# Kept in sync with catalog.ANIMAL_NAME_POOL; inlined so the migration has no app imports.
_NAME_POOL = (
    "Леонардо", "Микеланджело", "Рафаэль", "Донателло", "Боттичелли", "Тициан",
    "Караваджо", "Джотто", "Дюрер", "Босх", "Веласкес", "Тинторетто", "Веронезе",
    "Джорджоне", "Беллини", "Мантенья", "Верроккьо", "Перуджино", "Гольбейн", "Кранах",
    "Брунеллески", "Гиберти", "Браманте", "Челлини", "Палладио",
    "Галилей", "Коперник", "Кеплер", "Везалий", "Бруно", "Парацельс", "Кардано",
    "Данте", "Петрарка", "Боккаччо", "Макиавелли", "Эразм", "Монтень", "Рабле",
    "Шекспир", "Сервантес", "Колумб", "Магеллан", "Веспуччи", "Дрейк",
    "Медичи", "Лоренцо", "Козимо", "Гутенберг", "Америго", "Никколо", "Сандро",
    "Джулиано", "Пико",
)


def upgrade() -> None:
    op.add_column("animals", sa.Column("name", sa.String(length=32), nullable=True))
    conn = op.get_bind()
    ids = [row[0] for row in conn.execute(sa.text("SELECT id FROM animals WHERE name IS NULL"))]
    stmt = sa.text("UPDATE animals SET name = :name WHERE id = :id")
    for animal_id in ids:
        conn.execute(stmt, {"name": random.choice(_NAME_POOL), "id": animal_id})


def downgrade() -> None:
    op.drop_column("animals", "name")
