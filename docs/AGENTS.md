# Documentation Instructions

## Purpose

Документация в этой папке описывает текущую рабочую архитектуру, а не исторические намерения.

## Rules

- Если меняется backend topology, обновляй `/home/maxggor/Desktop/webzooparkbot/docs/api-migration-mixed-mode.md`.
- Не оставляй в docs старые описания entrypoint'ов или route-префиксов.
- Если документ описывает API, сверяй его с текущими `AGENTS.md` и gateway-тестами.

## Topology Source Of Truth

- `api.main:app` — stable entrypoint for the canonical ZooPark app
- `api.app.main:app` — canonical ZooPark app
- `/api/*` — current ZooPark product contracts
- `/v2/api/*` — removed from runtime and should not be documented as active

## When Updating Docs

- Обновляй абсолютные пути к ключевым файлам, если они упоминаются.
- Не документируй предположения как факт.
- Если topology изменилась, убедись, что тесты в `/home/maxggor/Desktop/webzooparkbot/api/tests/test_api_gateway.py` отражают то же состояние.
