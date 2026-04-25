# Backend Instructions

## Scope

This directory contains the stable ZooPark entrypoint plus the canonical structured backend.

Do not mix them casually.

## Architecture Rules

- ZooPark contracts on `/api/*` remain the source of truth for the current frontend.
- Canonical ZooPark backend logic belongs in `/home/maxggor/Desktop/webzooparkbot/api/app`.
- The app assembly is defined in `/home/maxggor/Desktop/webzooparkbot/api/main.py`.
- ZooPark `/api/*` routes should live in first-class `zoopark_*.py` route modules.

## When Working In `api/main.py`

- Treat it as app assembly and gateway composition only.
- Do not place product business logic here.
- If functionality changes, implement it in `api/app/...` and wire it from `api/main.py`.

## When Working In `api/app`

- Keep new code layered: routes -> schemas/core/db -> zoopark service modules.
- Avoid creating cycles between `api.main` and `api/app/routes/zoopark_*.py`.

## Route Safety

- If changing gateway behavior, update `/home/maxggor/Desktop/webzooparkbot/api/tests/test_api_gateway.py`.
