# ZooPark Domain Modules

## Purpose

`/home/maxggor/Desktop/webzooparkbot/api/app/zoopark` contains the migrated ZooPark domain logic that serves legacy `/api/*` contracts through the new backend architecture.

This directory is the extraction target for code that previously lived in `/home/maxggor/Desktop/webzooparkbot/api/main.py`.

## Rules

- Keep business logic here, not in `api/app/api/routes/zoopark_*.py`.
- Preserve current `/api/*` request and response contracts unless a coordinated frontend migration is explicitly requested.
- Prefer extracting shared helpers here instead of copying logic between domain modules.
- Do not reintroduce `api.main` imports from these modules.
- If a module becomes too broad, split it by subdomain rather than creating a new monolith.

## Current Domain Split

- `runtime.py`: DB access, auth, runtime config.
- `bootstrap.py`: legacy schema/bootstrap helpers.
- `catalog.py`: ZooPark catalogue and economy constants.
- `profile.py`: shared profile/state assembly helpers.
- `income.py`: pack-animal income helpers.
- `merchant.py`: merchant offers and purchases.
- `forge.py`: forge inventory and crafting.
- `social.py`: top, clans, referrals, transfer links.
- `games.py`: multiplayer, solo, donate, cocktail.
- `progression.py`: packs, localities, breeding, expeditions.

## Safe Change Pattern

1. Extract or update domain logic in this directory.
2. Wire the corresponding `zoopark_*.py` route module to these functions.
3. Update tests under `/home/maxggor/Desktop/webzooparkbot/api/tests`.
4. Only then remove obsolete compatibility glue.
