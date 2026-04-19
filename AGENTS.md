# Repository Instructions

## Project Shape

This repository now ships a single canonical ZooPark runtime.

- Frontend lives in `/home/maxggor/Desktop/webzooparkbot/src`.
- Stable backend entrypoint lives in `/home/maxggor/Desktop/webzooparkbot/api/main.py`.
- Canonical backend implementation lives in `/home/maxggor/Desktop/webzooparkbot/api/app`.
- Runtime topology notes live in `/home/maxggor/Desktop/webzooparkbot/docs/api-migration-mixed-mode.md`.

Read the nearest `AGENTS.md` before changing code in a subdirectory.

## Non-Negotiable Rules

- Do not silently change public API contracts used by the current frontend.
- Do not reintroduce dormant `/v2` or mixed-mode runtime codepaths.
- Keep ZooPark-owned persistence isolated from unrelated schemas.
- Do not edit generated or vendor directories such as `dist/` or `node_modules/`.

## Current API Topology

- `api.main:app` is the stable entrypoint for the canonical ZooPark app.
- `api.app.main:app` is the canonical ZooPark app.
- ZooPark routes live on `/api/*`.
- `/v2/api/*` is not mounted and should not be reintroduced.
- ZooPark `/api/*` HTTP routes should live in normal `api/app/api/routes/zoopark_*.py` modules.

If you change route topology, you must update:

- `/home/maxggor/Desktop/webzooparkbot/docs/api-migration-mixed-mode.md`
- `/home/maxggor/Desktop/webzooparkbot/api/tests/test_api_gateway.py`

## Validation

Minimum checks after meaningful changes:

- Frontend: `npm run build`
- Backend static syntax: `python3 -m py_compile ...`
- Gateway topology: `python3 -m unittest -v api.tests.test_api_gateway`
