# New Backend Architecture

## Purpose

`/home/maxggor/Desktop/webzooparkbot/api/app` is the structured backend for the current combined application.

It serves both native `/v2/api/*` functionality and migrated ZooPark `/api/*` logic.

## Layering

- `api/app/main.py`: app assembly and gateway composition only.
- `api/app/api/routes`: HTTP transport layer.
- `api/app/zoopark`: migrated ZooPark business logic serving legacy `/api/*` contracts.
- `api/app/services`: domain logic.
- `api/app/models`: ORM entities.
- `api/app/schemas`: request/response schemas.
- `api/app/domain`: shared balance/constants logic.
- `api/app/core`: framework glue such as auth/errors.

## Rules

- Keep route handlers thin.
- Put business logic in services, not directly in routes.
- Prefer dedicated service/domain modules for both `/v2/api/*` and migrated ZooPark logic.
- Do not add legacy ZooPark response shapes to native v2 endpoints.
- Do not make `api/app` depend on frontend-specific temporary hacks when a serializer/service boundary can express the rule.

## Mixed-Mode Constraint

- The combined gateway mounts native routes under `/v2` to avoid collisions with legacy `/api/*`.
- ZooPark `/api/*` routes should be organized in `api/app/api/routes/zoopark_*.py` modules.
- ZooPark route modules should call `api/app/zoopark/*` modules directly; do not reintroduce delegate shims back into `api.main`.

## Safe Change Pattern

1. Add or refactor logic in services/models/schemas.
2. Wire native route behavior.
3. Wire the corresponding ZooPark route module to the extracted domain module.
4. Keep gateway tests passing.
