"""Repeatable large-zoo benchmark for the read paths used by the mobile client.

Run from the repository root::

    api/.venv/bin/python api/scripts/benchmark_large_zoo.py --animals 11500 --runs 3

The database is in-memory SQLite and is discarded at exit by default.  Pass
``--database /tmp/large-zoo.sqlite3 --seed-only`` to retain the exact same dataset for
manual dev-server testing.  Setup time is deliberately excluded from measurements.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, event, select
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import api.app.db.connection as connection  # noqa: E402
from api.app.db.models import Animal, Base, Locality, Player, utcnow  # noqa: E402
from api.app.db.seed import seed_reference_data  # noqa: E402
from api.app.schemas.core import RegisterBody  # noqa: E402
from api.app.schemas.forge import ForgeActivateBody, ForgeCreateBody, ForgeItemIdBody, ForgeMergeBody, ForgeSetBody, ForgeSetIdBody  # noqa: E402
from api.app.zoopark import core, forge, ledger, progression, social  # noqa: E402
from api.app.zoopark.income import sync_player_income  # noqa: E402
from api.app.zoopark.profile import get_player  # noqa: E402


def _build_zoo(animal_count: int, database: Path | None = None) -> int:
    if database is None:
        engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    else:
        if database.exists():
            raise SystemExit(f"Refusing to overwrite existing database: {database}")
        database.parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(f"sqlite:///{database}", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _foreign_keys(dbapi_connection, _record) -> None:
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    connection._engine = engine
    connection._session_factory.configure(bind=engine)
    seed_reference_data()
    core.register(9_900_001, RegisterBody(nickname="large-zoo-benchmark"))

    now = utcnow()
    with connection.get_session() as session:
        player = session.scalar(select(Player).where(Player.telegram_id == 9_900_001))
        assert player is not None
        locality = session.scalar(select(Locality).where(Locality.player_id == player.id))
        assert locality is not None
        rows = [
            {
                "player_id": player.id,
                "season_id": locality.season_id,
                "species_id": index % 40 + 1,
                "name": f"Animal {index}",
                "is_favorite": index % 101 == 0,
                "locality_id": locality.id if index % 2 == 0 else None,
                "gene_survival": ("low", "medium", "high")[index % 3],
                "gene_reproduction": ("medium", "high", "low")[index % 3],
                "gene_appearance": ("high", "low", "medium")[index % 3],
                "gene_size": ("low", "high", "medium")[index % 3],
                "habitat": locality.habitat,
                "origin": "pack",
                "acquired_at": now - timedelta(seconds=index),
                "dies_at": now + timedelta(days=30, seconds=index),
                "removed_at": None,
                "removal_reason": None,
                "sick_since": now if index % 997 == 0 else None,
                "last_bred_on": None,
                "parent_a_id": None,
                "parent_b_id": None,
            }
            for index in range(animal_count)
        ]
        session.execute(Animal.__table__.insert(), rows)
        session.commit()
    return 9_900_001


def _measure(name: str, operation: Callable[[], Any], runs: int) -> None:
    engine = connection._engine
    query_count = 0

    def before_cursor_execute(*_args) -> None:
        nonlocal query_count
        query_count += 1

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    samples: list[float] = []
    sizes: list[int] = []
    try:
        for _ in range(runs):
            query_count = 0
            started = time.perf_counter()
            result = operation()
            encoded = json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode()
            samples.append((time.perf_counter() - started) * 1_000)
            sizes.append(len(encoded))
        median_ms = statistics.median(samples)
        print(
            f"{name:24} median={median_ms:9.2f} ms  min={min(samples):9.2f} ms  "
            f"json={statistics.median(sizes) / 1_048_576:6.2f} MiB  sql={query_count}"
        )
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)


def _measure_mutation(
    name: str,
    prepare: Callable[[], Any],
    operation: Callable[[Any], Any],
    runs: int,
) -> None:
    engine = connection._engine
    query_count = 0

    def before_cursor_execute(*_args) -> None:
        nonlocal query_count
        query_count += 1

    event.listen(engine, "before_cursor_execute", before_cursor_execute)
    samples: list[float] = []
    sizes: list[int] = []
    try:
        for _ in range(runs):
            context = prepare()
            query_count = 0
            started = time.perf_counter()
            result = operation(context)
            encoded = json.dumps(result, ensure_ascii=False, separators=(",", ":")).encode()
            samples.append((time.perf_counter() - started) * 1_000)
            sizes.append(len(encoded))
        print(
            f"{name:24} median={statistics.median(samples):9.2f} ms  min={min(samples):9.2f} ms  "
            f"json={statistics.median(sizes) / 1_048_576:6.2f} MiB  sql={query_count}"
        )
    finally:
        event.remove(engine, "before_cursor_execute", before_cursor_execute)


def _grant(tg_id: int, currency: str, amount: int) -> None:
    with connection.get_session() as session:
        player = get_player(session, tg_id, for_update=True)
        assert player is not None
        ledger.grant(session, player, currency, amount, "benchmark_grant")
        session.commit()


def _force_income_recalculation(tg_id: int) -> dict:
    with connection.get_session() as session:
        player = get_player(session, tg_id, for_update=True)
        assert player is not None
        income, upkeep = sync_player_income(session, player)
        session.commit()
        return {"income": income, "upkeep": upkeep}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--animals", type=int, default=11_500)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--database", type=Path)
    parser.add_argument("--seed-only", action="store_true")
    parser.add_argument("--mutations", action="store_true")
    args = parser.parse_args()

    print(f"Preparing {args.animals:,} animals...")
    tg_id = _build_zoo(args.animals, args.database)
    if args.database is not None:
        print(f"Database: {args.database}")
        print(f"DEV_TG_ID={tg_id}")
    if args.seed_only:
        return
    _measure("GET /api/me", lambda: core.me(tg_id), args.runs)
    _measure("GET /api/profile", lambda: social.public_profile(tg_id, tg_id), args.runs)
    _measure("GET /api/zoo/animals", lambda: progression.list_zoo_animals(tg_id), args.runs)
    _measure("zoo sort=income", lambda: progression.list_zoo_animals(tg_id, sort="income"), args.runs)
    _measure("zoo sort=quality", lambda: progression.list_zoo_animals(tg_id, sort="quality"), args.runs)
    _measure("income recalculation", lambda: _force_income_recalculation(tg_id), args.runs)
    _measure("GET /api/zoo/forecast", lambda: progression.animal_forecast(tg_id), args.runs)
    _measure("legacy breeding (unused)", lambda: progression.list_breeding_animals(tg_id), args.runs)
    _measure("GET /api/breeding/page", lambda: progression.list_breeding_animals_page(tg_id), args.runs)
    _measure("breeding sort=income", lambda: progression.list_breeding_animals_page(tg_id, sort="income"), args.runs)
    _measure("GET /api/expeditions", lambda: progression.get_expeditions(tg_id), args.runs)
    _measure("GET /api/expeditions/page", lambda: progression.list_expedition_animals_page(tg_id), args.runs)
    _measure("legacy localities (bots)", lambda: progression.list_localities(tg_id), args.runs)
    _measure("GET /localities/summary", lambda: progression.list_localities_summary(tg_id), args.runs)
    _measure("GET /localities/page", lambda: progression.list_locality_animals_page(tg_id), args.runs)
    if args.mutations:
        mutation_runs = min(args.runs, 3)
        _grant(tg_id, "usd", 10 ** 12)
        _grant(tg_id, "paw", 10 ** 9)
        _measure("POST pack x1", lambda: progression.open_pack(tg_id, "rare", 1), mutation_runs)
        _measure("POST pack x10", lambda: progression.open_pack(tg_id, "rare", 10), mutation_runs)
        _measure("POST pack x100", lambda: progression.open_pack(tg_id, "rare", 100), mutation_runs)
        _measure("POST forge/create", lambda: forge.forge_create(tg_id, ForgeCreateBody(currency="usd")), mutation_runs)

        def prepare_item() -> int:
            return int(forge.forge_create(tg_id, ForgeCreateBody(currency="usd"))["item"]["id"])

        _measure_mutation(
            "POST forge/upgrade",
            prepare_item,
            lambda item_id: forge.forge_upgrade(tg_id, ForgeItemIdBody(item_id=item_id)),
            mutation_runs,
        )
        _measure_mutation(
            "POST forge/sell",
            prepare_item,
            lambda item_id: forge.forge_sell(tg_id, ForgeItemIdBody(item_id=item_id)),
            mutation_runs,
        )
        _measure_mutation(
            "POST forge/activate",
            prepare_item,
            lambda item_id: forge.forge_activate(tg_id, ForgeActivateBody(item_id=item_id)),
            mutation_runs,
        )

        def prepare_merge() -> tuple[int, int]:
            first = prepare_item()
            second = prepare_item()
            return first, second

        _measure_mutation(
            "POST forge/merge",
            prepare_merge,
            lambda ids: forge.forge_merge(tg_id, ForgeMergeBody(item_id1=ids[0], item_id2=ids[1])),
            mutation_runs,
        )

        def prepare_set() -> int:
            item_id = prepare_item()
            created = forge.forge_set_create(tg_id, ForgeSetBody(item_ids=[item_id]))
            return int(created["set"]["id"])

        _measure_mutation(
            "POST forge/set apply",
            prepare_set,
            lambda set_id: forge.forge_set_apply(tg_id, ForgeSetIdBody(set_id=set_id)),
            mutation_runs,
        )


if __name__ == "__main__":
    main()
