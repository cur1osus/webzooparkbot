"""Set the house's balance for one currency to an exact amount.

An operational lever, not a game action: the treasury has no write endpoint, because
nothing in the game is supposed to move it except bank commissions and the safe. Seeding
it by hand is legitimate exactly once — to give the safe something to pay out before real
commissions have accumulated.

It goes through `ledger.credit_treasury` / `ledger.debit_treasury` rather than assigning
to the row, so the same row lock every bank exchange takes still applies and a deploy
running mid-exchange cannot lose a commission.

    python -m api.scripts.set_treasury --currency usd --amount 100000 [--dry-run]
"""

from __future__ import annotations

import argparse

from api.app.db.connection import get_session
from api.app.zoopark import ledger
from api.app.zoopark.catalog import CURRENCIES


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--currency", default="usd", choices=sorted(CURRENCIES))
    parser.add_argument("--amount", type=int, required=True, help="target balance, not a delta")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.amount < 0:
        raise SystemExit("amount must not be negative")

    with get_session() as session:
        current = ledger.treasury_balance(session, args.currency)
        delta = args.amount - current
        print(f"treasury {args.currency}: {current} -> {args.amount} (delta {delta:+})")

        if args.dry_run:
            print("dry run, nothing written")
            return
        if delta > 0:
            ledger.credit_treasury(session, args.currency, delta, "admin_adjust")
        elif delta < 0:
            taken = ledger.debit_treasury(session, args.currency, -delta, "admin_adjust")
            if taken != -delta:
                raise SystemExit(f"expected to take {-delta}, took {taken}; aborted without commit")

        session.commit()
        print(f"treasury {args.currency} is now {ledger.treasury_balance(session, args.currency)}")


if __name__ == "__main__":
    main()
