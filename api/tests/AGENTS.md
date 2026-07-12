# Test Instructions

## Purpose

These tests defend invariants, not implementation details. Each one names the hole it keeps
shut.

## They run against the real schema

`conftest.py` creates `Base.metadata` in an in-memory SQLite database with foreign keys on.
The previous suite mocked `get_session` and asserted on the mock, so it could not have
caught a missing unique key, a lost row lock, or a ledger that disagreed with a balance.

Do not go back to mocking the session. If a test needs a player, use the `player` fixture;
if it needs money, use `grant`.

## What must keep a test

- `test_economy_invariants.py` — the bank has no reverse conversion; forging never
  out-earns its cost; the house keeps an edge in solo games; **every item property has a
  live consumer**. Extend it whenever you touch a price.
- `test_ledger.py` — nothing assigns a balance outside `ledger.grant()`, and the ledger
  reconciles with every balance.
- `test_progression.py` — the GDD's numbers: 40/40/20 gene rolls, the breeding table, and
  that an expedition can actually be lost.
- `test_income.py` — the GDD's 12:1 income spread, the diversity entropy, and that a
  fraction of a ruble does not reset the accrual clock.
- `test_star_payments.py` — crediting is idempotent, refunds claw back, and the webhook
  handler is not a coroutine.
- `test_auth.py` — initData verification and the production config checks.

## Rules

- Do not delete an invariant test because it blocks a refactor. Change the invariant on
  purpose, then change the test.
- Prefer a deterministic check over a probabilistic one. Where a test must sample (win
  rates, gene inheritance), assert a band wide enough not to flake and narrow enough to
  catch an inverted comparison.
