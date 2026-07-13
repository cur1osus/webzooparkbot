# ZooPark

Telegram Mini App: a zoo-management game. React + Vite on the front, FastAPI + MySQL on the back.
The canonical design is `Merchant's Menagerie GDD v1.0`; where the code departs from it, the
departure is named and justified in a comment (see `api/app/zoopark/catalog.py`).

## Layout

| Path | What lives there |
| --- | --- |
| `src/` | React app (pages, API client, zustand store) |
| `api/main.py` | App assembly only — no business logic |
| `api/app/core` | Config, Telegram auth, Bot API client |
| `api/app/routes` | HTTP transport, one module per domain |
| `api/app/schemas` | Pydantic request bodies |
| `api/app/db` | Schema and seeding |
| `api/app/zoopark` | Business logic |
| `api/migrations` | Alembic revisions |

## Running locally

```bash
# Backend
python3.12 -m venv api/.venv
api/.venv/bin/pip install -r api/requirements.txt
cp .env.example .env && set -a && . ./.env && set +a
api/.venv/bin/alembic -c api/alembic.ini upgrade head
api/.venv/bin/uvicorn api.main:app --reload --port 8001

# Frontend
npm ci
npm run dev
```

With `APP_ENV=development` and `DEV_AUTH=1` you can authenticate outside Telegram: the
frontend stores a `dev_user_id` in `localStorage` and sends it as `X-Dev-User-Id`.

## Environment

| Variable | Required | Default | Purpose |
| --- | --- | --- | --- |
| `APP_ENV` | no | `production` | `development` relaxes the startup checks below |
| `BOT_TOKEN` | in production | — | Verifies Telegram `initData` and calls the Bot API |
| `BOT_USERNAME` | development fallback | `ZooParkBot` | Used only when Telegram Bot API is unavailable outside production; production resolves the username via `getMe` |
| `TELEGRAM_WEBHOOK_SECRET` | in production | — | Authenticates `/api/telegram/webhook` |
| `DEV_AUTH` | no | `0` | Allows the `X-Dev-User-Id` bypass. **Never enable in production** |
| `ALLOWED_TG_IDS` | no | `474701274` | CSV whitelist; `*` opens the game to everyone |
| `INIT_DATA_MAX_AGE_SECONDS` | no | `86400` | Rejects replayed `initData` older than this |
| `DB_HOST` / `DB_PORT` / `DB_USER` / `DB_PASSWORD` / `DB_NAME` | yes | `127.0.0.1` / `3306` / `admin_zoopark` / — / `zoopark` | MySQL connection |
| `VITE_API_URL` | no | `/api` | Frontend API base (build time) |

In production the app **refuses to start** when `BOT_TOKEN` or `TELEGRAM_WEBHOOK_SECRET`
are missing, or when `DEV_AUTH` is on. Each of those silently disabled a security control
before.

There is no `BANK_RATE_SECRET`. The bank rate used to be `HMAC(secret, current_minute)` —
a pure function of the clock, which needed a secret to stop clients precomputing it. It is
now a random walk stored in `bank_rates`, and state needs no secret to be unpredictable.

## Money

Three currencies, all server-authoritative, all `BIGINT`, none ever negative.

**Nothing may assign to `player.balance_*`.** The only door is `ledger.grant()`, which
writes a row into `ledger` carrying the delta, the reason and the balance it produced.
`test_no_module_assigns_a_balance_directly` greps the domain package to keep it that way,
and `test_ledger_reconciles_with_every_balance` asserts `SUM(delta) == balance`.

Every endpoint that moves currency first takes a row lock via
`profile.get_player(session, tg_id, for_update=True)`.

### The bank is one-way

Rubles come out of the zoo; dollars buy forge upgrades. `POST /api/bank/exchange` converts
`rub → usd` and there is no reverse direction. That is what makes a visibly swinging rate
safe to publish: waiting for a cheap minute gets you more dollars, and there is no way to
sell them back into a dear one.

The previous bank quoted both directions around a ±15% oscillation with a 2% spread, so
buying low and selling high returned 26% per round trip, risk-free and unbounded.

### Upkeep

Animals cost `income × (5% + 12% × log₁₀(count))`, capped at 45%. It is the only ruble sink
that scales with success. Not a GDD feature — ported from the Telegram bot, because GDD §8
assumes weak animals stop paying for themselves mid-season, which requires holding one to
cost something.

## Derived state is never stored

An animal is alive iff `removed_at IS NULL AND dies_at > now`. There is no `is_alive`
column, so there is no sweeper job whose absence makes `/api/me` serve dead animals earning
money — which is exactly what used to happen.

Likewise `players.income_rub_per_min` *is* a cache, and says so: `income.sync_player_income`
recomputes it after any change to the zoo or the player's items, and the leaderboard reads
the indexed column instead of scanning every animal of every player twice.

## Forge items do things

Every property an item can roll names the function that reads it, in
`ITEM_PROPERTIES[kind]["applies_to"]`. `test_every_item_property_is_applied` fails if you
add a property without wiring it up. Before the rewrite the forge sold artefacts labelled
"Общий доход +45%" for Telegram Stars and nothing anywhere read the number.

`duel_moves` and `duel_bonus` apply only to player-versus-player duels, where the pot is
zero-sum. They deliberately never touch solo games: the 4% house edge there is the only
thing draining rubles out of the casino.

## Telegram Stars

Payments only land if the bot's webhook points at `/api/telegram/webhook` with the matching
`secret_token`. `deploy.sh` registers it (step 8/9).

* `telegram_updates.update_id` makes every update idempotent, not just the paying ones.
* Crediting is idempotent on `star_payments.charge_id`.
* `refunded_payment` claws the PawCoins back. Without it a player could buy 1 000 PawCoins,
  ask Telegram for the Stars back, and keep both.
* The webhook handler is `def`, not `async def`. On the event loop its blocking Bot API call
  and `SELECT … FOR UPDATE` could freeze every request for every player for the length of
  MySQL's lock timeout.

### Notifications

Expedition completion, animal death and daily-bonus readiness are delivered through the
durable `notification_outbox`. The game mutation and its notification event commit
together; a background worker sends due rows with exponential retry. Delivery is
at-least-once, so a process crash immediately after Telegram accepts a message can cause
one duplicate, while a temporary Bot API failure cannot lose the event or roll back game
state.

## Checks

```bash
pytest api/tests -q                       # 131 tests, on the real schema in SQLite
mypy api/app --ignore-missing-imports     # must stay clean
ruff check api                            # bug-catching rules only
npm run lint && npm test && npm run build # frontend
```

`api/tests/test_economy_invariants.py` guards the rules that keep the economy closed:
the bank has no reverse conversion, forging never out-earns its cost, the house keeps an
edge in solo games, every item property has a live consumer. Add to it when you touch prices.

`api/tests/test_progression.py` guards the GDD: 40/40/20 gene rolls, the breeding table,
and — the one the old code got wrong — that an expedition can actually be lost.

`api/tests/test_migration_matches_models.py` runs `alembic upgrade head` and diffs the
result against `Base.metadata`. Autogenerate is off; nothing else stops the revision and
the ORM from drifting apart.

## The client tells the truth

Three screens used to promise effects nobody implemented, and all three now say what the
server actually does:

* the zoo's `Видов (+N%)` badge renders `diversity_bonus_percent`, the bonus the server
  applied, instead of multiplying two numbers the client happened to have;
* the pack tiers are labels for the price of the Nth pack of the day. GDD §1 rolls genes
  40/40/20 in every one of them, so they no longer advertise "улучшенные гены";
* clans have no specialities. The picker offered four of them, `get_clan` returned
  `specialty: None` every time, and no code read the field.

There is no autosave. `/api/save` ran every 15 seconds to POST a `data_version` the server
stored and handed straight back.

## Deploy

`./deploy.sh` builds the frontend, uploads both halves, backs up MySQL, runs Alembic,
verifies the revision is at head, restarts the API, waits for `/api/health` (including a
live database probe), and registers the Telegram webhook.

### Migration history

The schema is a linear Alembic history ending in `20260713_0014_pack_price_usd.py`.
Deployments run `alembic upgrade head` only after creating a `mysqldump`, then verify that
the database revision equals the application head.

Do not drop the production database to resolve a migration mismatch. If a legacy database
points at a revision that is not in this checkout, stop the deployment and reconcile its
Alembic version table with the migration history using the backup and a reviewed migration
plan. The deploy script deliberately fails before restart when `upgrade head` or the head
check fails.
