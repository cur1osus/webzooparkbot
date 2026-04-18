# API Topology

## Current Topology

- `api.main:app` is the compatibility entrypoint for the current ZooPark app.
- `api.app.main:app` is the primary application entrypoint.
- ZooPark HTTP routes live on `/api/*` and are the canonical product API.
- `/v2/api/*` is no longer mounted at runtime.

## Route Hosting

- ZooPark `/api/*` routes are assembled from `zoopark_*.py` route modules in `api/app/api/routes/`.
- ZooPark business logic lives in `api/app/zoopark/`.
- Schema/bootstrap is initialized from `api/app/main.py`.
- Core endpoints are hosted under `/api/*`, including `/api/health`, `/api/me`, `/api/save`, `/api/register`, `/api/config`, `/api/buy_animal`, `/api/buy_aviary`, `/api/bank`, `/api/bank/exchange`, `/api/claim_bonus`, `/api/cure_animal`.
- `api/app/api/routes/zoopark_economy.py` preserves the current bank exchange request contract: frontend still sends `{ "from": "rub" | "usd", "amount": number }`.
- Remaining ZooPark domains are split by business area in `api/app/zoopark/merchant.py`, `forge.py`, `social.py`, `games.py`, and `progression.py`.

## Runtime Objects

- `api.main:app` points to the current ZooPark app.
- `api.main:legacy_app` is kept only as an alias to the same app for compatibility with old process targets.
- `api.app.main:app` is the primary ZooPark app.

## Compatibility Note

- `api/main.py` is a thin compatibility shell only.
- The old mixed-mode boot path through preserved `legacy_main*.pyc` artifacts is removed.
- Current work should treat `api/app/...` as the only active backend implementation.

## Data Topology

- ZooPark runtime uses dedicated ZooPark tables for user-owned entities to avoid collisions with unrelated product schemas.
- Generic names like `users`, `animals`, `aviaries`, `items`, `unity` are no longer assumed to belong to ZooPark runtime code.

## Direction

1. Keep `api/main.py` as a stable entrypoint only.
2. Continue cleaning and splitting `api/app/zoopark/*` as the canonical backend.
3. Preserve current `/api/*` contracts used by the shipped frontend.

Backend changes that affect gateway composition must still be reflected in `api/tests/test_api_gateway.py`.
