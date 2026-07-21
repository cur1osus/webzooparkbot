# Backend Instructions

## Scope

`api/` is the FastAPI backend. `api/main.py` assembles the app; everything else lives in
`api/app`. See `api/app/AGENTS.md` for the layering and
`api/app/zoopark/AGENTS.md` for the rules that keep the economy closed.

## Architecture Rules

- `/api/*` contracts are the source of truth for the frontend in `src/`. Changing one means
  changing `src/types` and `src/api` in the same commit.
- Business logic lives in `api/app/zoopark`, never in `api/main.py` or a route module.
- Route modules are `api/app/routes/zoopark_*.py`. They authenticate with the `TelegramId`
  dependency, parse a schema, and call one domain function.
- No cycles: `api/app/*` never imports `api.main`.

## When Working In `api/main.py`

- App assembly only: middleware, routers, the lifespan hook.
- The lifespan validates config and seeds reference data. It does not create tables —
  that is Alembic's job, and running both was how the schema drifted.

## Route Safety

- Handlers are `def`, not `async def`. The Telegram webhook makes a blocking HTTP call and
  takes row locks; on the event loop it could freeze every request for every player.
- Any new endpoint that moves currency takes a row lock and goes through `ledger.grant()`.

## Tests

- `pytest api/tests -q` runs the suite on in-memory SQLite. Fast, and what CI runs first.
- **Before touching anything that stores a timestamp or a large blob, run it on MySQL too:**
  `TEST_DB_URL='mysql+pymysql://user@/zoopark_test?unix_socket=/tmp/mysql.sock' pytest api/tests -q`.
  SQLite's `TEXT` is unbounded and MySQL's is 64 KiB; SQLite keeps microseconds in a
  `DATETIME` and MySQL drops them. Both differences have reached production, the second one
  as a money exploit — accrual measured from a rounded-down anchor paid a polling client
  258x. The suite passes on both engines; keep it that way.
