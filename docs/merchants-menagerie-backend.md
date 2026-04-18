# Merchant's Menagerie Backend

## What Was Replaced

The previous backend stored game state through a legacy `pymysql` monolith with broad tables and JSON blobs. The new backend is split into a domain-oriented FastAPI application under `/home/maxggor/Desktop/webzooparkbot/api/app` and uses SQLAlchemy ORM models with explicit relationships.

## New Core Aggregates

- `players`: player identity bound to Telegram auth.
- `seasons`: global 30-day season windows.
- `player_seasons`: seasonal player progress and coin balance.
- `player_habitats`: unlocked terrain zones for the current seasonal zoo.
- `animals`: individual animal instances with genes, lifespan, current placement, status, and parent relationships.
- `pack_openings`: auditable pack open events and generated reward animal.
- `breeding_attempts`: breeding history, success chance, and offspring link.
- `expeditions`: expedition lifecycle, resolved outcome, wild animal snapshot, gained/lost animal.
- `expedition_party_members`: many-to-many relation between an expedition and the participating animals.

## Implemented HTTP Core

- `GET /api/health`
- `GET /api/config`
- `POST /api/register`
- `GET /api/me`
- `POST /api/packs/open`
- `POST /api/habitats/unlock`
- `POST /api/animals/{animal_id}/assign-habitat`
- `POST /api/breeding/attempt`
- `POST /api/expeditions`
- `POST /api/expeditions/{expedition_id}/resolve`

## Important GDD Inferences

The GDD does not define several absolute economy numbers, so they are centralized in `/home/maxggor/Desktop/webzooparkbot/api/app/domain/balance.py` instead of being hard-coded inside handlers.

- Starting coins
- Base paid pack price and daily growth multiplier
- Base habitat unlock price
- Base animal income per hour

The GDD also does not explicitly define income for unplaced animals. The current implementation treats unassigned animals as generating no income until they are placed into an unlocked habitat.

## Migration

Alembic revision `0006` performs a destructive schema reset and recreates the database for the new GDD model. This matches the approved scope: no data migration from the old game is preserved.

The backend now supports `DB_URL` override for test and CI scenarios. If `DB_URL` is not provided, it falls back to the MySQL connection assembled from `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, and `DB_NAME`.

## Verification Commands

- Unit tests: `python3 -m unittest discover -s /home/maxggor/Desktop/webzooparkbot/api/tests -v`
- SQLite migration smoke: `cd /home/maxggor/Desktop/webzooparkbot/api && DB_URL=sqlite:////tmp/merchants_menagerie_smoke.db python3 -m alembic -c alembic.ini upgrade head`
