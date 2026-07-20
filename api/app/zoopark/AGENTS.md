# ZooPark Domain Modules

## Purpose

`api/app/zoopark` holds the game. Routes call into it; it never calls back out.

## Money Rules

These are not style preferences. Every one of them was a live exploit.

- **`ledger.grant()` is the only door.** Nothing else may assign to `player.balance_rub`,
  `balance_usd` or `balance_paw`. `test_no_module_assigns_a_balance_directly` greps this
  package to keep it that way, and `test_ledger_reconciles_with_every_balance` asserts
  `SUM(delta) == balance` for each currency.
- **The house has its own journal.** `credit_treasury`/`debit_treasury` are the only way
  the `treasury` row moves, they take a `TreasuryReason`, and they write `treasury_ledger`.
  `test_the_treasury_journal_reconciles_with_the_row` asserts `SUM(delta) == balance` there
  too. Book what actually moved, not what was requested — `debit_treasury` caps at the
  balance and journals the capped amount.
- **Lock before you spend.** Anything that moves currency loads the player with
  `profile.get_player(session, tg_id, for_update=True)`, and locks every other row it
  mutates (duel, item, offer, transfer).
- **The client never sets a balance.** Never read a currency off a request body.
- **Integers only.** A float amount was once charged truncated and credited in full.
- **Charge what you credit.** Compute the debit and the credit from the same quantity.
- **No sink pays more than its source costs.** Selling < forging; the house edge stays
  positive; the bank has no reverse conversion to arbitrage.
  `api/tests/test_economy_invariants.py` enforces this — extend it when you add a price.
- **Randomness that decides money uses `SystemRandom`.** The bank rate is *state*
  (`bank_rates`), a random walk, not a function of the clock — so it needs no secret.
- **Money from outside is idempotent.** Stars are credited once per
  `telegram_payment_charge_id`, and `refunded_payment` takes the PawCoins back.
- **GETs do not mutate game outcomes.** Resolving an expedition, rolling a reward — POST.

## Feature Rules

- **A property a player can buy must do something.** Every entry in
  `catalog.ITEM_PROPERTIES` names the function that reads it in `applies_to`, and
  `test_every_item_property_is_applied` fails otherwise. The forge once sold
  "Общий доход +45%" for Telegram Stars and nothing read the number.
- **Derived state is not stored.** An animal is alive iff
  `removed_at IS NULL AND dies_at > now`. Do not add an `is_alive` column back.
- **`players.income_rub_per_min` is a cache.** Anything that changes the zoo or the
  player's items calls `income.sync_player_income` before it returns.

## Domain Split

- `catalog.py`: every balance constant and the species list. No database rows.
- `ledger.py`: currency movement and the treasury. `debit_treasury` is capped at the
  balance and returns what it actually took — credit that number, never the number you
  asked for, or the safe pays out dollars the house does not have.
- `bonuses.py`: what a player's active items add up to.
- `income.py`: income, upkeep, diversity, passive accrual.
- `profile.py`: reads — the player row, the zoo, `build_state`.
- `core.py`: registration and `/api/me`.
- `economy.py`: the bank. One-way, `rub → usd`.
- `progression.py`: packs, localities, breeding, expeditions.
- `merchant.py`: the three daily offers.
- `forge.py`: items, their properties, sets.
- `games.py`: duels, solo games, cocktail, Telegram Stars.
- `safe.py`: the bank safe — the only path out of the treasury.
- `social.py`: leaderboard, clans, referrals, transfers.
- `status.py`: the daily bonus and curing animals.
- `season.py`: the 30-day season.

## Safe Change Pattern

1. Change the constant in `catalog.py`, not a literal at the call site.
2. Change the domain function here.
3. Keep request bodies in `api/app/schemas`.
4. Wire the `zoopark_*.py` route module.
5. Add the invariant to `api/tests`, then remove obsolete glue.
