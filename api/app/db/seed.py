"""Seeds the reference tables from `catalog.py`.

Replaces `bootstrap.py`, which ran `Base.metadata.create_all()` on every start alongside
Alembic and copied rows out of the Telegram bot's tables. The two apps have separate
databases; there was nothing left to copy, and the schema is Alembic's job alone.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from api.app.db.connection import get_session
from api.app.db.models import SeasonGate, Species, Treasury
from api.app.zoopark.catalog import CURRENCIES, SPECIES

logger = logging.getLogger(__name__)


def seed_species(session: Session) -> None:
    """Upsert by id. Deleting first would break the foreign keys from `animals`."""
    for index, spec in enumerate(SPECIES, start=1):
        row = session.get(Species, index)
        if row is None:
            session.add(
                Species(
                    id=index,
                    code=spec["code"],
                    name=spec["name"],
                    emoji=spec["emoji"],
                    rarity=spec["rarity"],
                )
            )
            continue
        row.code = spec["code"]
        row.name = spec["name"]
        row.emoji = spec["emoji"]
        row.rarity = spec["rarity"]


def seed_treasury(session: Session) -> None:
    for currency in CURRENCIES:
        if session.get(Treasury, currency) is None:
            session.add(Treasury(currency=currency, balance=0))


def seed_season_gate(session: Session) -> None:
    if session.get(SeasonGate, 1) is None:
        session.add(SeasonGate(id=1))


def seed_reference_data() -> None:
    with get_session() as session:
        seed_species(session)
        seed_treasury(session)
        seed_season_gate(session)
        session.commit()
    logger.info("Seeded %d species", len(SPECIES))
