# Repository Instructions

## Project Shape

This repository is in a mixed-mode migration state.

- Frontend lives in `/home/maxggor/Desktop/webzooparkbot/src`.
- Compatibility backend entrypoint lives in `/home/maxggor/Desktop/webzooparkbot/api/main.py`.
- New backend architecture lives in `/home/maxggor/Desktop/webzooparkbot/api/app`.
- Migration notes live in `/home/maxggor/Desktop/webzooparkbot/docs/api-migration-mixed-mode.md`.

Read the nearest `AGENTS.md` before changing code in a subdirectory.

## Non-Negotiable Rules

- Do not treat this repo as a clean greenfield rewrite. Old and new architectures coexist intentionally.
- Do not silently change public API contracts used by the current frontend.
- Do not move legacy behavior into the new domain model without an explicit migration seam.
- Do not edit generated or vendor directories such as `dist/` or `node_modules/`.

## Current API Topology

- `api.main:app` is the compatibility entrypoint for the combined gateway app.
- `api.main:legacy_app` is the preserved legacy ZooPark app kept for compatibility.
- `api.app.main:app` is the combined gateway app.
- Legacy ZooPark routes stay on `/api/*`.
- Native Merchant's Menagerie routes are mounted under `/v2/api/*`.
- ZooPark `/api/*` HTTP routes should live in normal `api/app/api/routes/zoopark_*.py` modules.

If you change route topology, you must update:

- `/home/maxggor/Desktop/webzooparkbot/docs/api-migration-mixed-mode.md`
- `/home/maxggor/Desktop/webzooparkbot/api/tests/test_api_gateway.py`

## Validation

Minimum checks after meaningful changes:

- Frontend: `npm run build`
- Backend static syntax: `python3 -m py_compile ...`
- Gateway topology: `python3 -m unittest -v api.tests.test_api_gateway`
