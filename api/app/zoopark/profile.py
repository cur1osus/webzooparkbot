"""Reading a player: the row itself, their zoo, their forge, and the state the client renders."""

from __future__ import annotations

from datetime import datetime
from typing import cast

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.app.db.models import Animal, Clan, ClanMember, Item, ItemSet, Locality, Player, PlayerCosmetic, Season, utcnow
from api.app.zoopark import achievements as achievements_module
from api.app.zoopark import bonuses as bonuses_module
from api.app.zoopark.bonuses import Bonuses
from api.app.zoopark.catalog import (
    BASE_INCOME_RUB_PER_MIN,
    DIVERSITY_BONUS_PERCENT_PER_SPECIES,
    GENE_INCOME_MULT,
    HABITAT_MATCH_BONUS,
    ITEM_PROPERTIES,
    NICKNAME_COLORS,
    PROFILE_FRAMES,
    PROFILE_WALLPAPERS,
    SPECIES_BY_ID,
    SPECIES_RARITY_INCOME_MULT,
    SICK_INCOME_MULT,
    PropertyKind,
    item_sell_price_usd,
)
from api.app.zoopark.income import (
    alive_animals,
    animal_income,
    cure_cost_usd,
    diversity_multiplier,
    effective_species_count,
)
from api.app.zoopark.season import ensure_player_season


def get_player(session: Session, telegram_id: int, *, for_update: bool = False) -> Player | None:
    """`for_update=True` takes a row lock — mandatory for anything that moves currency."""
    stmt = select(Player).where(Player.telegram_id == telegram_id)
    if for_update:
        stmt = stmt.with_for_update()
    player = session.scalars(stmt).first()
    if player is not None and player.status == "banned":
        raise HTTPException(403, "Аккаунт заблокирован")
    return player


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _property_payload(item: Item) -> list[dict]:
    payload = []
    for prop in sorted(item.properties, key=lambda p: (p.kind, p.species_id or 0)):
        spec = ITEM_PROPERTIES.get(cast(PropertyKind, prop.kind))
        species = SPECIES_BY_ID.get(prop.species_id) if prop.species_id else None
        payload.append(
            {
                "kind": prop.kind,
                "value": prop.value,
                "species_code": species["code"] if species else None,
                "label": property_label(prop.kind, prop.value, species["name"] if species else None),
                "unit": spec["unit"] if spec else "flat",
            }
        )
    return payload


def property_label(kind: str, value: int, species_name: str | None = None) -> str:
    spec = ITEM_PROPERTIES.get(cast(PropertyKind, kind))
    if spec is None:
        return f"{kind} {value}"
    label = spec["label"]
    if spec["per_species"] and species_name:
        label = f"{label}: {species_name}"
    if spec["unit"] == "percent_bonus":
        return f"{label} +{value}%"
    if spec["unit"] == "percent_discount":
        return f"{label} −{value}%"
    return f"{label} +{value}"


def item_payload(item: Item) -> dict:
    return {
        "id": str(item.id),
        "name": item.name,
        "icon": item.emoji,
        "rarity": item.rarity,
        "level": item.level,
        "is_active": bool(item.is_active),
        "sell_price_usd": item_sell_price_usd(item.rarity, item.level),  # type: ignore[arg-type]
        "properties": _property_payload(item),
    }


def list_items(session: Session, player_id: int) -> list[dict]:
    items = session.scalars(
        select(Item).where(Item.player_id == player_id).order_by(Item.created_at.asc(), Item.id.asc())
    ).all()
    return [item_payload(item) for item in items]


def list_item_sets(session: Session, player_id: int) -> list[dict]:
    sets = session.scalars(
        select(ItemSet).where(ItemSet.player_id == player_id).order_by(ItemSet.created_at.asc(), ItemSet.id.asc())
    ).all()
    active_ids = {
        str(row) for row in session.scalars(
            select(Item.id).where(Item.player_id == player_id, Item.is_active.is_(True))
        ).all()
    }

    payload = []
    for item_set in sets:
        member_ids = [str(m.item_id) for m in sorted(item_set.members, key=lambda m: m.position)]
        payload.append(
            {
                "id": str(item_set.id),
                "name": item_set.name,
                "icon": item_set.emoji,
                "item_ids": member_ids,
                "is_active": bool(member_ids) and set(member_ids) == active_ids,
            }
        )
    return payload


def animal_income_breakdown(animal: Animal, locality_habitat: str | None, bonuses: Bonuses) -> dict:
    species = SPECIES_BY_ID[animal.species_id]
    matches = bool(locality_habitat) and locality_habitat == animal.habitat
    is_sick = animal.sick_since is not None
    species_multiplier = bonuses.species_income_multiplier(animal.species_id)
    rarity_multiplier = SPECIES_RARITY_INCOME_MULT[species["rarity"]]
    factors = [
        {"key": "survival", "label": "Выживаемость", "value": animal.gene_survival, "multiplier": GENE_INCOME_MULT["survival"][animal.gene_survival]},
        {"key": "appearance", "label": "Внешность", "value": animal.gene_appearance, "multiplier": GENE_INCOME_MULT["appearance"][animal.gene_appearance]},
        {"key": "size", "label": "Размер", "value": animal.gene_size, "multiplier": GENE_INCOME_MULT["size"][animal.gene_size]},
        {"key": "habitat", "label": "Родная среда", "value": "да" if matches else "нет", "multiplier": HABITAT_MATCH_BONUS if matches else 1.0},
        {"key": "sickness", "label": "Здоровье", "value": "болен" if is_sick else "здоров", "multiplier": SICK_INCOME_MULT if is_sick else 1.0},
        {"key": "species_item", "label": "Предметы вида", "value": "активные" if species_multiplier != 1.0 else "нет", "multiplier": species_multiplier},
    ]
    return {
        "base": round(BASE_INCOME_RUB_PER_MIN * rarity_multiplier),
        "factors": factors,
        "total": animal_income(animal, locality_habitat, bonuses),
    }


def animal_payload(animal: Animal, locality_habitat: str | None, bonuses: Bonuses, today=None, vet_level: int = 0) -> dict:
    species = SPECIES_BY_ID[animal.species_id]
    day = today or utcnow().date()
    matches = bool(locality_habitat) and locality_habitat == animal.habitat
    income_breakdown = animal_income_breakdown(animal, locality_habitat, bonuses)
    return {
        "id": animal.id,
        "name": animal.name or species["name"],
        "species_code": species["code"],
        "species_name": species["name"],
        "species_emoji": species["emoji"],
        "species_rarity": species["rarity"],
        "survival": animal.gene_survival,
        "reproduction": animal.gene_reproduction,
        "appearance": animal.gene_appearance,
        "size_trait": animal.gene_size,
        "habitat": animal.habitat,
        "origin": animal.origin,
        "acquired_at": _iso(animal.acquired_at),
        "dies_at": _iso(animal.dies_at),
        "locality_id": animal.locality_id,
        "is_sick": animal.sick_since is not None,
        "can_breed": animal.last_bred_on != day,
        "income": income_breakdown["total"],
        "income_breakdown": income_breakdown,
        "cure_cost_usd": cure_cost_usd(animal, locality_habitat, bonuses, vet_level),
        "habitat_bonus": matches,
        "parent_a_id": animal.parent_a_id,
        "parent_b_id": animal.parent_b_id,
    }


def get_clan(session: Session, player_id: int) -> dict | None:
    membership = session.scalars(select(ClanMember).where(ClanMember.player_id == player_id)).first()
    if membership is None:
        return None
    clan = session.get(Clan, membership.clan_id)
    if clan is None:
        return None
    member_count = len(session.scalars(select(ClanMember.player_id).where(ClanMember.clan_id == clan.id)).all())
    return {
        "id": clan.id,
        "name": clan.name,
        "level": clan.level,
        "member_count": member_count,
        "role": membership.role,
    }


def nickname_colors_payload(session: Session, player_id: int) -> list[dict]:
    owned = set(session.scalars(
        select(PlayerCosmetic.cosmetic_id).where(PlayerCosmetic.player_id == player_id)
    ).all())
    return [
        {
            "id": color_id,
            "price_paw": spec["price_paw"],
            "animated": spec["animated"],
            "rarity": spec["rarity"],
            "owned": color_id == "ivory" or color_id in owned,
        }
        for color_id, spec in NICKNAME_COLORS.items()
    ]


def profile_frames_payload(session: Session, player_id: int) -> list[dict]:
    owned = set(session.scalars(
        select(PlayerCosmetic.cosmetic_id).where(PlayerCosmetic.player_id == player_id)
    ).all())
    return [
        {
            "id": frame_id,
            "price_paw": spec["price_paw"],
            "animated": spec["animated"],
            "rarity": spec["rarity"],
            "owned": frame_id == "none" or f"frame:{frame_id}" in owned,
        }
        for frame_id, spec in PROFILE_FRAMES.items()
    ]


def profile_wallpapers_payload(session: Session, player_id: int) -> list[dict]:
    owned = set(session.scalars(
        select(PlayerCosmetic.cosmetic_id).where(PlayerCosmetic.player_id == player_id)
    ).all())
    return [
        {
            "id": wallpaper_id,
            "price_paw": spec["price_paw"],
            "animated": spec["animated"],
            "rarity": spec["rarity"],
            "owned": wallpaper_id == "none" or f"wall:{wallpaper_id}" in owned,
        }
        for wallpaper_id, spec in PROFILE_WALLPAPERS.items()
    ]


def build_state(session: Session, player: Player) -> dict:
    season: Season = ensure_player_season(session, player)
    bonuses = bonuses_module.load(session, player.id)

    rows = alive_animals(session, player.id, season.id)
    today = utcnow().date()
    animals = [animal_payload(animal, habitat, bonuses, today, player.vet_level) for animal, habitat in rows]

    counts_by_species: dict[int, int] = {}
    for animal, _habitat in rows:
        counts_by_species[animal.species_id] = counts_by_species.get(animal.species_id, 0) + 1

    localities_count = len(
        session.scalars(
            select(Locality.id).where(Locality.player_id == player.id, Locality.season_id == season.id)
        ).all()
    )

    items = list_items(session, player.id)
    counts = list(counts_by_species.values())
    diversity = diversity_multiplier(counts)

    return {
        "tg_id": player.telegram_id,
        "nickname": player.nickname,
        "nickname_color": player.nickname_color,
        "nickname_colors": nickname_colors_payload(session, player.id),
        "profile_frame": player.profile_frame,
        "profile_frames": profile_frames_payload(session, player.id),
        "profile_wallpaper": player.profile_wallpaper,
        "profile_wallpapers": profile_wallpapers_payload(session, player.id),
        "registered_at": _iso(player.registered_at),
        "profile_emoji": player.profile_emoji,
        "rub": player.balance_rub,
        "usd": player.balance_usd,
        "paw_coins": player.balance_paw,
        "vet_level": player.vet_level,
        "genetics_level": player.genetics_level,
        "income_rub_per_min": player.income_rub_per_min,
        "upkeep_rub_per_min": player.upkeep_rub_per_min,
        "income_synced_at": _iso(player.income_synced_at),
        "animals": animals,
        "sick_animal_ids": [a["id"] for a in animals if a["is_sick"]],
        "species_count": len(counts_by_species),
        # What the diversity bonus is actually computed from, so the client can stop
        # rendering a percentage the server never applied.
        "effective_species_count": round(effective_species_count(counts), 2),
        "diversity_bonus_percent": round((diversity - 1) * 100, 2),
        "live_animals_count": len(animals),
        "localities_count": localities_count,
        "season_id": season.id,
        "season_started_at": _iso(season.starts_at),
        "season_ends_at": _iso(season.ends_at),
        "items": items,
        "item_sets": list_item_sets(session, player.id),
        "clan": get_clan(session, player.id),
        "achievements": achievements_module.list_achievements(session, player),
        "diversity_bonus_percent_per_species": DIVERSITY_BONUS_PERCENT_PER_SPECIES,
    }
