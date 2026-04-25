# New Backend Architecture

## Purpose

`/home/maxggor/Desktop/webzooparkbot/api/app` is the structured backend for the canonical ZooPark application.

## Layering

- `api/main.py`: app assembly and gateway composition only.
- `api/app/core`: runtime config and Telegram auth helpers.
- `api/app/db`: database connection, table names, and persistence bootstrap helpers.
- `api/app/schemas`: Pydantic request/response models.
- `api/app/routes`: HTTP transport layer.
- `api/app/zoopark`: ZooPark business logic serving `/api/*` contracts.

## Rules

- Keep route handlers thin.
- Put ZooPark business logic in `api/app/zoopark`, not directly in routes.
- Do not reintroduce dormant `/v2` modules, models, or service layers.
- Do not make `api/app` depend on frontend-specific temporary hacks when a route/domain boundary can express the rule.

## Topology Constraint

- ZooPark `/api/*` routes should be organized in `api/app/routes/zoopark_*.py` modules.
- ZooPark route modules should authenticate, parse schemas, and call `api/app/zoopark/*` service modules; do not reintroduce delegate shims back into `api.main`.

## Safe Change Pattern

1. Add or refactor schemas in `api/app/schemas` when request/response shapes change.
2. Add or refactor business logic in `api/app/zoopark`.
3. Wire the corresponding ZooPark route module.
4. Keep gateway and route tests passing.
