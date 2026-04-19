# New Backend Architecture

## Purpose

`/home/maxggor/Desktop/webzooparkbot/api/app` is the structured backend for the canonical ZooPark application.

## Layering

- `api/app/main.py`: app assembly and gateway composition only.
- `api/app/api/routes`: HTTP transport layer.
- `api/app/zoopark`: ZooPark business logic serving `/api/*` contracts.

## Rules

- Keep route handlers thin.
- Put ZooPark business logic in `api/app/zoopark`, not directly in routes.
- Do not reintroduce dormant `/v2` modules, models, or service layers.
- Do not make `api/app` depend on frontend-specific temporary hacks when a route/domain boundary can express the rule.

## Topology Constraint

- ZooPark `/api/*` routes should be organized in `api/app/api/routes/zoopark_*.py` modules.
- ZooPark route modules should call `api/app/zoopark/*` modules directly; do not reintroduce delegate shims back into `api.main`.

## Safe Change Pattern

1. Add or refactor logic in `api/app/zoopark`.
2. Wire the corresponding ZooPark route module.
3. Keep gateway tests passing.
