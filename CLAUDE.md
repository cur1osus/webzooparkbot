# CLAUDE.md

Этот файл оставлен только как совместимый указатель для LLM-агентов, которые читают именно `CLAUDE.md`.

Актуальные инструкции по архитектуре и правилам работы находятся в `AGENTS.md` рядом с кодом.

## Читать в таком порядке

1. `/home/maxggor/Desktop/webzooparkbot/AGENTS.md`
2. `/home/maxggor/Desktop/webzooparkbot/api/AGENTS.md` при работе с backend
3. `/home/maxggor/Desktop/webzooparkbot/api/app/AGENTS.md` при работе с новым backend
4. `/home/maxggor/Desktop/webzooparkbot/src/AGENTS.md` при работе с frontend
5. `/home/maxggor/Desktop/webzooparkbot/docs/AGENTS.md` при изменении документации
6. `/home/maxggor/Desktop/webzooparkbot/api/tests/AGENTS.md` при изменении тестов

## Ключевой факт про архитектуру

Репозиторий находится в mixed-mode migration состоянии:

- `api.main:app` — compatibility entrypoint на combined gateway
- `api.main:legacy_app` — сохраненный legacy ZooPark app для совместимости
- `api.app.main:app` — combined gateway app
- legacy ZooPark маршруты живут на `/api/*`
- native Merchant's Menagerie маршруты живут на `/v2/api/*`

Не доверяй старым описаниям архитектуры из прошлых сессий. Если локальный `AGENTS.md` противоречит старым заметкам, источник правды — `AGENTS.md`.

## Обязательные файлы для mixed-mode API

- `/home/maxggor/Desktop/webzooparkbot/docs/api-migration-mixed-mode.md`
- `/home/maxggor/Desktop/webzooparkbot/api/tests/test_api_gateway.py`

Если меняешь topology, route inventory или migration seam, обновляй документацию и gateway-тесты вместе с `zoopark_*.py` route-модулями.
