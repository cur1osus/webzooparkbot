"""The travelling merchant: three visible animals a day, priced by what they will earn.

Not a GDD feature. An offer is one concrete animal with its genes on display, so its
price comes from `merchant_price_rub(genes)` — a fixed share of that animal's own lifetime
earnings. The old code took the price from a dead `animals_info.price` column, where a
rabbit cost 1 100 ₽ and a narwhal 268 000 000 000 ₽ for animals whose income was identical.
"""

from __future__ import annotations

from datetime import timedelta
from typing import cast

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.app.db.connection import get_session
from api.app.db.models import MerchantOffer, utcnow
from api.app.zoopark import bonuses as bonuses_module
from api.app.zoopark import ledger
from api.app.zoopark.bonuses import Bonuses
from api.app.zoopark.catalog import (
    MERCHANT_DISCOUNTS,
    MERCHANT_REFRESH_HOURS,
    MERCHANT_SLOTS,
    SPECIES_BY_ID,
    GeneTier,
    Rarity,
    merchant_price_rub,
)
from api.app.zoopark.income import sync_player_income
from api.app.zoopark.profile import animal_payload, get_player
from api.app.zoopark.progression import create_animal, random, roll_genes, roll_habitat, roll_species_id
from api.app.zoopark.season import ensure_player_season


def offer_price_rub(offer: MerchantOffer, bonuses: Bonuses) -> int:
    """List price minus the merchant's own per-offer discount. (Item discounts now apply to
    packs, not the merchant — see the `discount_packs` property.)"""
    del bonuses  # kept for call-site compatibility; the merchant has no item discount now
    return max(1, int(offer_list_price_rub(offer) * (100 - offer.discount_pct) / 100))


def offer_list_price_rub(offer: MerchantOffer) -> int:
    species = SPECIES_BY_ID[offer.species_id]
    return merchant_price_rub(
        cast(GeneTier, offer.gene_survival),
        cast(GeneTier, offer.gene_appearance),
        cast(GeneTier, offer.gene_size),
        cast(Rarity, species["rarity"]),
    )


def _fresh_offer(player_id: int, season_id: int, slot: int, expires_at) -> MerchantOffer:
    genes = roll_genes()
    species_id = roll_species_id()
    return MerchantOffer(
        player_id=player_id,
        season_id=season_id,
        slot=slot,
        species_id=species_id,
        habitat=roll_habitat(),
        discount_pct=random.choice(MERCHANT_DISCOUNTS),
        list_price_rub=merchant_price_rub(
            genes["gene_survival"],
            genes["gene_appearance"],
            genes["gene_size"],
            SPECIES_BY_ID[species_id]["rarity"],  # type: ignore[arg-type]
        ),
        expires_at=expires_at,
        **genes,
    )


def ensure_offers(session: Session, player_id: int, season_id: int) -> list[MerchantOffer]:
    """Exactly `MERCHANT_SLOTS` rows, refreshed when they expire.

    `uq_merchant_offers_slot` is what makes this safe: two concurrent reads cannot end up
    with six offers, because the second insert into a taken slot loses.
    """
    now = utcnow()
    existing = list(
        session.scalars(
            select(MerchantOffer)
            .where(MerchantOffer.player_id == player_id, MerchantOffer.season_id == season_id)
            .order_by(MerchantOffer.slot.asc())
        ).all()
    )
    by_slot = {offer.slot: offer for offer in existing}
    expires_at = now + timedelta(hours=MERCHANT_REFRESH_HOURS)

    for slot in range(1, MERCHANT_SLOTS + 1):
        offer = by_slot.get(slot)
        if offer is None:
            try:
                with session.begin_nested():
                    session.add(_fresh_offer(player_id, season_id, slot, expires_at))
            except IntegrityError:
                pass
        elif offer.expires_at <= now:
            genes = roll_genes()
            offer.species_id = roll_species_id()
            offer.habitat = roll_habitat()
            offer.discount_pct = random.choice(MERCHANT_DISCOUNTS)
            offer.list_price_rub = merchant_price_rub(
                genes["gene_survival"],
                genes["gene_appearance"],
                genes["gene_size"],
                SPECIES_BY_ID[offer.species_id]["rarity"],  # type: ignore[arg-type]
            )
            offer.purchased_at = None
            offer.created_at = now
            offer.expires_at = expires_at
            for key, value in genes.items():
                setattr(offer, key, value)
        elif offer.purchased_at is None:
            # Reprice unbought offers when the balance constants change, so an old row
            # never keeps a stale pre-rebase price until its next daily rotation.
            offer.list_price_rub = offer_list_price_rub(offer)

    session.flush()
    return list(
        session.scalars(
            select(MerchantOffer)
            .where(MerchantOffer.player_id == player_id, MerchantOffer.season_id == season_id)
            .order_by(MerchantOffer.slot.asc())
        ).all()
    )


def _offer_payload(offer: MerchantOffer, bonuses: Bonuses) -> dict:
    species = SPECIES_BY_ID[offer.species_id]
    return {
        "slot": offer.slot,
        "species_code": species["code"],
        "species_name": species["name"],
        "species_emoji": species["emoji"],
        "species_rarity": species["rarity"],
        "survival": offer.gene_survival,
        "reproduction": offer.gene_reproduction,
        "appearance": offer.gene_appearance,
        "size_trait": offer.gene_size,
        "habitat": offer.habitat,
        "list_price": offer_list_price_rub(offer),
        "discount_pct": offer.discount_pct,
        "final_price": offer_price_rub(offer, bonuses),
        "bought": offer.purchased_at is not None,
    }


def merchant_animals(tg_id: int) -> dict:
    with get_session() as session:
        player = get_player(session, tg_id)
        if not player:
            raise HTTPException(404, "Нет игрока")
        season = ensure_player_season(session, player)
        offers = ensure_offers(session, player.id, season.id)
        bonuses = bonuses_module.load(session, player.id)
        payload = [_offer_payload(offer, bonuses) for offer in offers]
        refreshes_at = min(offer.expires_at for offer in offers) if offers else utcnow()
        session.commit()
        return {"animals": payload, "refreshes_at": refreshes_at.isoformat()}


def buy_offer(tg_id: int, slot: int) -> dict:
    if not (1 <= slot <= MERCHANT_SLOTS):
        raise HTTPException(400, "Неверный слот")

    with get_session() as session:
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Нет игрока")
        sync_player_income(session, player)
        season = ensure_player_season(session, player)
        ensure_offers(session, player.id, season.id)

        offer = session.scalars(
            select(MerchantOffer)
            .where(
                MerchantOffer.player_id == player.id,
                MerchantOffer.season_id == season.id,
                MerchantOffer.slot == slot,
            )
            .with_for_update()
        ).first()
        if offer is None:
            raise HTTPException(400, "Неверный слот")
        if offer.purchased_at is not None:
            raise HTTPException(400, "Уже куплено")
        if offer.expires_at <= utcnow():
            raise HTTPException(400, "Предложение истекло")

        bonuses = bonuses_module.load(session, player.id)
        price = offer_price_rub(offer, bonuses)
        ledger.spend(session, player, "rub", price, "merchant_buy", ref_table="merchant_offers", ref_id=offer.id)

        animal = create_animal(
            session,
            player_id=player.id,
            season_id=season.id,
            origin="merchant",
            genes={
                "gene_survival": offer.gene_survival,  # type: ignore[dict-item]
                "gene_reproduction": offer.gene_reproduction,  # type: ignore[dict-item]
                "gene_appearance": offer.gene_appearance,  # type: ignore[dict-item]
                "gene_size": offer.gene_size,  # type: ignore[dict-item]
            },
            habitat=offer.habitat,  # type: ignore[arg-type]
            species_id=offer.species_id,
        )
        offer.purchased_at = utcnow()

        sync_player_income(session, player, bonuses)
        result = {
            "ok": True,
            "price_paid": price,
            "new_rub": ledger.balance(player, "rub"),
            "animal": animal_payload(animal, None, bonuses),
        }
        session.commit()
        return result
