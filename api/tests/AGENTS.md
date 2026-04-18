# Test Instructions

## Purpose

Тесты в этой папке защищают текущие архитектурные и доменные инварианты.

## Gateway Tests

`/home/maxggor/Desktop/webzooparkbot/api/tests/test_api_gateway.py` защищает mixed-mode API seam.

Если меняется что-то из списка ниже, тест нужно пересмотреть вместе с кодом:

- legacy route inventory
- combined gateway assembly
- mount `/v2`
- способ регистрации legacy-роутов

## Rules

- Не удаляй gateway-тест просто потому, что он мешает рефакторингу.
- Сначала измени архитектуру осознанно, потом обнови тест под новый intended state.
- Не превращай topology-тест в smoke без проверок контрактных путей.

## Minimum Expectations

- Для legacy/gateway изменений должен оставаться тестовый сигнал на наличие ключевых путей:
  `/api/me`, `/api/save`, `/api/expeditions/finish`, `/v2`
- Для новых тестов prefer deterministic checks over environment-sensitive integration hacks.
