# Test Instructions

## Purpose

Тесты в этой папке защищают текущие архитектурные и доменные инварианты.

## Gateway Tests

`/home/maxggor/Desktop/webzooparkbot/api/tests/test_api_gateway.py` защищает канонический ZooPark gateway seam.

Если меняется что-то из списка ниже, тест нужно пересмотреть вместе с кодом:

- legacy route inventory
- app assembly
- canonical `/api/*` route inventory
- thin `api/main.py` entrypoint

## Rules

- Не удаляй gateway-тест просто потому, что он мешает рефакторингу.
- Сначала измени архитектуру осознанно, потом обнови тест под новый intended state.
- Не превращай topology-тест в smoke без проверок контрактных путей.

## Minimum Expectations

- Для legacy/gateway изменений должен оставаться тестовый сигнал на наличие ключевых путей:
  `/api/health`, `/api/me`, `/api/save`, `/api/expeditions/finish`
- Для новых тестов prefer deterministic checks over environment-sensitive integration hacks.
