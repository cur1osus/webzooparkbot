# Frontend Instructions

## Current Contract Reality

The current frontend is bound to canonical ZooPark `/api/*` contracts.

## Architecture Rules

- `src/api.ts` is the only place for HTTP contract definitions and fetch wrappers.
- `src/types.ts` is the single source of truth for frontend API/data shapes.
- Pages should consume typed API helpers, not inline `fetch`.
- Keep presentational helpers reusable when multiple pages share domain visuals.

## State Rules

- `src/store.ts` owns server load, silent persistence, and IndexedDB cache shape.
- Do not change the persisted game-state shape casually.
- If backend contracts change, update API helpers, types, and state transitions together.

## Backend Notes

- `/api/*` is the only supported product API for the shipped frontend.
- Do not add frontend dependencies on dormant `/v2` contracts or deleted backend experiments.
- If backend contracts change, migrate API wrapper, types, UI state, and regression checks together.

## Validation

- Always run `npm run build` after frontend changes.
- If you change shared API/types, sanity-check all affected pages instead of only the page you edited.
