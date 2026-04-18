# Backend Instructions

## Scope

This directory contains the combined gateway entrypoint plus the new structured backend.

Do not mix them casually.

## Architecture Rules

- ZooPark contracts on `/api/*` remain the source of truth for the current frontend.
- New Merchant's Menagerie logic belongs in `/home/maxggor/Desktop/webzooparkbot/api/app`.
- The combined gateway is defined in `/home/maxggor/Desktop/webzooparkbot/api/app/main.py`.
- ZooPark `/api/*` routes in the combined gateway should live in first-class `zoopark_*.py` route modules.

## When Working In `api/main.py`

- Treat it as a thin compatibility shell only.
- Do not place product logic here.
- If functionality changes, implement it in `api/app/...` and keep `api/main.py` as an import-stable entrypoint.

## When Working In `api/app`

- Keep new code layered: routes -> services -> models/schemas.
- Do not import `api.app.main` from legacy routing or bootstrapping modules.
- Avoid creating cycles between `api.main`, `api.app.main`, and `api/app/api/routes/zoopark_*.py`.

## Route Safety

- If changing gateway behavior, update `/home/maxggor/Desktop/webzooparkbot/api/tests/test_api_gateway.py`.
