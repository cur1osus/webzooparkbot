"""What a player's active forge items actually do.

The Telegram bot kept this as `users.info_about_items`, a JSON blob rebuilt by hand every
time an item was toggled. Here it is one aggregate over `item_properties`, so it cannot
fall out of sync with the items it summarises.

Rules, unchanged from the bot: only active items count, at most `FORGE_MAX_ACTIVE_ITEMS`
of them, values of the same kind sum, and the sum is clipped to the kind's cap.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.app.db.models import Item, ItemProperty
from api.app.zoopark.catalog import ITEM_PROPERTIES, PropertyKind


@dataclass(frozen=True)
class Bonuses:
    """Summed, capped values of every property on the player's active items."""

    _global: dict[str, int] = field(default_factory=dict)
    _by_species: dict[tuple[str, int], int] = field(default_factory=dict)

    def total(self, kind: PropertyKind) -> int:
        """Value of a kind that applies to everything, e.g. `income_total`."""
        return self._global.get(kind, 0)

    def for_species(self, kind: PropertyKind, species_id: int) -> int:
        """Value of a per-species kind, e.g. `income_species` for the giraffes you own."""
        return self._by_species.get((kind, species_id), 0)

    def income_multiplier(self) -> float:
        return 1 + self.total("income_total") / 100

    def species_income_multiplier(self, species_id: int) -> float:
        return 1 + self.for_species("income_species", species_id) / 100

    def upkeep_discount_multiplier(self) -> float:
        return 1 - self.total("discount_upkeep") / 100

    def pack_discount_multiplier(self) -> float:
        return 1 - self.total("discount_packs") / 100

    def locality_discount_multiplier(self) -> float:
        return 1 - self.total("discount_locality") / 100

    def bank_rate_multiplier(self) -> float:
        """A lower rate means fewer rubles per dollar, so the discount helps the buyer."""
        return 1 - self.total("discount_bank") / 100


EMPTY = Bonuses()


def _cap(kind: str, value: int) -> int:
    limit = ITEM_PROPERTIES[kind]["cap"] if kind in ITEM_PROPERTIES else None
    return min(value, limit) if limit is not None else value


def load(session: Session, player_id: int) -> Bonuses:
    rows = session.execute(
        select(
            ItemProperty.kind,
            ItemProperty.species_id,
            func.sum(ItemProperty.value).label("total"),
        )
        .join(Item, Item.id == ItemProperty.item_id)
        .where(Item.player_id == player_id, Item.is_active.is_(True))
        .group_by(ItemProperty.kind, ItemProperty.species_id)
    ).all()

    global_values: dict[str, int] = {}
    species_values: dict[tuple[str, int], int] = {}
    for kind, species_id, total in rows:
        value = _cap(kind, int(total or 0))
        if species_id is None:
            global_values[kind] = value
        else:
            species_values[(kind, int(species_id))] = value

    return Bonuses(_global=global_values, _by_species=species_values)
