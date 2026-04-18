# API Mixed-Mode Migration

## Current Topology

- `api.main:app` is now a compatibility entrypoint that exposes the combined gateway app.
- `api.app.main:app` is the combined gateway entrypoint.
- Legacy ZooPark routes stay on the original `/api/*` paths.
- Native `api/app/...` Merchant's Menagerie routes are mounted under `/v2/api/*`.

This gives the project one FastAPI application entrypoint while old and new game domains coexist during migration.

## Legacy Route Hosting

- ZooPark `/api/*` routes are assembled from first-class `zoopark_*.py` route modules in `api/app/api/routes/`.
- ZooPark business logic now lives in dedicated modules under `api/app/zoopark/`; the route layer no longer delegates back into `api/main.py`.
- Legacy schema/bootstrap is initialized from `api/app/main.py` through the old table bootstrap constants and helpers.
- The first migrated ZooPark endpoints now live natively in `api/app/api/routes/zoopark_core.py`, `api/app/api/routes/zoopark_economy.py`, and `api/app/api/routes/zoopark_status.py`: `/api/me`, `/api/save`, `/api/register`, `/api/config`, `/api/buy_animal`, `/api/buy_aviary`, `/api/bank`, `/api/bank/exchange`, `/api/claim_bonus`, `/api/cure_animal`.
- `api/app/api/routes/zoopark_economy.py` preserves the legacy bank exchange request contract: frontend still sends `{ "from": "rub" | "usd", "amount": number }`.
- Remaining migrated domains are split by business area in `api/app/zoopark/merchant.py`, `forge.py`, `social.py`, `games.py`, and `progression.py`.

## Runtime Objects

- `api.main:legacy_app` keeps the preserved legacy ZooPark app for compatibility.
- `api.main:app` is the compatibility entrypoint that now points to the combined gateway app.
- `api.app.main:app` is the combined gateway app.

## Compatibility Note

- `api/main.py` is a thin compatibility shell for the combined gateway.
- The legacy monolith source is no longer kept as the active implementation file.
- `api.main:legacy_app` first tries to load preserved legacy monolith bytecode from dedicated `legacy_main*.pyc` artifacts and otherwise falls back to the combined gateway app.
- This is a temporary compatibility bridge, not a target architecture. New work should continue in `api/app/...`.

## Migration Intent

The dedicated legacy API seam is closed.

The intended long-term direction is:

1. Keep `api/main.py` as a stable entrypoint only.
2. Continue cleaning and splitting `api/app/zoopark/*` as domain modules grow.
3. Preserve `/api/*` contracts until a coordinated frontend migration is approved.

Backend changes that affect gateway composition must still be reflected in `api/tests/test_api_gateway.py`.
