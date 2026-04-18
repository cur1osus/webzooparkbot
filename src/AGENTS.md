# Frontend Instructions

## Current Contract Reality

The current frontend is still bound to legacy ZooPark `/api/*` contracts.

Do not assume the native Merchant's Menagerie `/v2/api/*` responses can be consumed directly without an explicit frontend migration task.

## Architecture Rules

- `src/api.ts` is the only place for HTTP contract definitions and fetch wrappers.
- `src/types.ts` is the single source of truth for frontend API/data shapes.
- Pages should consume typed API helpers, not inline `fetch`.
- Keep presentational helpers reusable when multiple pages share domain visuals.

## State Rules

- `src/store.ts` owns server load, silent persistence, and IndexedDB cache shape.
- Do not change the persisted game-state shape casually.
- If backend contracts change, update API helpers, types, and state transitions together.

## Mixed-Mode Backend Notes

- `/api/*` currently means legacy ZooPark behavior.
- `/v2/api/*` is reserved for native structured backend work and should only be consumed when the task explicitly migrates a frontend slice.
- If you migrate a page from legacy to v2, do it end-to-end: API wrapper, types, UI state, and regression checks.

## Validation

- Always run `npm run build` after frontend changes.
- If you change shared API/types, sanity-check all affected pages instead of only the page you edited.
