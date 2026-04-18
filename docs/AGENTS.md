# Documentation Instructions

## Purpose

Документация в этой папке описывает текущую рабочую архитектуру, а не исторические намерения.

## Rules

- Если меняется backend topology, обновляй `/home/maxggor/Desktop/webzooparkbot/docs/api-migration-mixed-mode.md`.
- Не оставляй в docs старые описания entrypoint'ов или route-префиксов.
- Если документ описывает API, сверяй его с текущими `AGENTS.md` и gateway-тестами.

## Mixed-Mode Source Of Truth

- `api.main:app` — compatibility entrypoint on the combined gateway
- `api.main:legacy_app` — preserved legacy ZooPark app for compatibility
- `api.app.main:app` — combined gateway
- `/api/*` — legacy ZooPark contracts
- `/v2/api/*` — native Merchant's Menagerie contracts

## When Updating Docs

- Обновляй абсолютные пути к ключевым файлам, если они упоминаются.
- Не документируй предположения как факт.
- Если topology изменилась, убедись, что тесты в `/home/maxggor/Desktop/webzooparkbot/api/tests/test_api_gateway.py` отражают то же состояние.
