# Backend Architecture

## Purpose

`api/app` is the backend for ZooPark. The canonical game design is
`Merchant's Menagerie GDD v1.0`; departures from it are named in a comment where they live.

## Layering

- `api/main.py`: app assembly only. No business logic.
- `api/app/core`: runtime config, Telegram auth, Bot API client.
- `api/app/db`: schema (`models.py`), connection, reference-data seeding.
- `api/app/schemas`: Pydantic request bodies. Validate at the boundary, so bad input is a
  422 rather than a `ValueError` escaping the domain as a 500.
- `api/app/routes`: HTTP transport. Authenticate via the `TelegramId` dependency, parse a
  schema, call one domain function.
- `api/app/zoopark`: business logic.

## Rules

- Route handlers stay thin: auth, parse, delegate.
- The schema is Alembic's job alone. Nothing calls `create_all` at runtime.
- Handlers are `def`, not `async def`. Everything they do is blocking — a synchronous Bot
  API call and row locks — and on the event loop one of them can freeze the whole process.
- Do not make `api/app` depend on a frontend workaround when a domain boundary can express
  the rule instead.

## Safe Change Pattern

1. Change the schema in `api/app/db/models.py` and add an Alembic revision.
2. Change or add the request body in `api/app/schemas`.
3. Change the domain function in `api/app/zoopark`.
4. Wire the route module.
5. Extend the tests in `api/tests`, then remove the obsolete glue.
