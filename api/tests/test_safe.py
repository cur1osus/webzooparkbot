"""The bank safe: sealed windows, a code that outlives the day, and the treasury payout."""

from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from sqlalchemy.orm import Session

from api.app.db.connection import get_session
from api.app.db.models import LedgerEntry, Player, SafeAttempt, SafeRound, TreasuryLedgerEntry
from api.app.schemas.core import RegisterBody
from api.app.schemas.games import SafeGuessBody
from api.app.zoopark import ledger, safe
from api.app.zoopark.core import register

# 2026-07-20, Moscow. The window runs 19:00–23:00 local, which is 16:00–20:00 UTC.
DAY = date(2026, 7, 20)
OPEN = datetime(2026, 7, 20, 16, 0, tzinfo=timezone.utc)
MIDWINDOW = OPEN + timedelta(hours=1)
CLOSED = OPEN + timedelta(hours=5)
NEXT_DAY = OPEN + timedelta(days=1, hours=1)

# Коды длиной SAFE_CODE_LENGTH с проверенными подсказками, чтобы смена длины правилась
# в одном месте, а не в тридцати литералах.
SECRET = "401729"
NEAR = "401000"       # (3, 0) — три цифры на месте
SCRAMBLED = "297401"  # (0, 6) — те же цифры, все не на месте
MISS = "888888"       # (0, 0)
OTHER_MISS = "777777"


@pytest.fixture()
def at(monkeypatch):
    """Freeze the clock the safe module reads."""

    def _set(moment: datetime) -> datetime:
        monkeypatch.setattr(safe, "utcnow", lambda: moment)
        return moment

    return _set


def _register(*telegram_ids: int) -> None:
    for index, telegram_id in enumerate(telegram_ids, start=1):
        register(telegram_id, RegisterBody(nickname=f"player-{index}"))


def _fill_treasury(amount: int) -> None:
    with get_session() as session:
        ledger.credit_treasury(session, "usd", amount, "bank_fee")
        session.commit()


def _usd(telegram_id: int) -> int:
    with get_session() as session:
        return session.query(Player).filter_by(telegram_id=telegram_id).one().balance_usd


def _secret() -> str:
    with get_session() as session:
        return session.query(SafeRound).order_by(SafeRound.id.desc()).first().secret


def _force_secret(value: str, now: datetime = MIDWINDOW) -> None:
    """Open the round if it does not exist yet and pin its code, so a test can assert on
    clues instead of on whatever `SystemRandom` produced."""
    with get_session() as session:
        round_ = safe.current_round(session, now)
        round_.secret = value
        session.commit()


# ─── Window ───────────────────────────────────────────────────────────────────


def test_window_opens_at_19_and_closes_after_four_hours():
    assert safe.window(MIDWINDOW) == (DAY, OPEN, OPEN + timedelta(hours=4))
    assert safe.is_open(OPEN) is True
    assert safe.is_open(OPEN + timedelta(hours=3, minutes=59)) is True
    assert safe.is_open(OPEN + timedelta(hours=4)) is False
    assert safe.is_open(CLOSED) is False


def test_morning_belongs_to_the_previous_evening_window():
    morning = datetime(2026, 7, 21, 7, 0, tzinfo=timezone.utc)
    assert safe.window(morning)[0] == DAY
    assert safe.is_open(morning) is False
    assert safe.last_closed_day(morning) == DAY


def test_last_closed_day_excludes_the_window_still_running():
    assert safe.last_closed_day(MIDWINDOW) == DAY - timedelta(days=1)
    assert safe.last_closed_day(CLOSED) == DAY


# ─── Scoring ──────────────────────────────────────────────────────────────────


def test_repeated_digits_are_counted_as_a_multiset():
    assert safe.score("1234", "1234") == (4, 0)
    assert safe.score("1234", "4321") == (0, 4)
    # `1111` shares only one digit with `1234`, not four.
    assert safe.score("1234", "1111") == (1, 0)
    assert safe.score("1122", "1212") == (2, 2)


# ─── Guessing ─────────────────────────────────────────────────────────────────


def test_guess_is_rejected_outside_the_window(db, at):
    _register(1001)
    at(CLOSED)
    with pytest.raises(HTTPException) as excinfo:
        safe.safe_guess(1001, SafeGuessBody(code=SECRET))
    assert excinfo.value.status_code == 400


def test_only_three_guesses_per_day(db, at):
    _register(1001)
    at(MIDWINDOW)
    for expected_left in (2, 1, 0):
        assert safe.safe_guess(1001, SafeGuessBody(code=SECRET))["attempts_left"] == expected_left
    with pytest.raises(HTTPException):
        safe.safe_guess(1001, SafeGuessBody(code=OTHER_MISS))


def test_malformed_codes_are_refused(db, at):
    _register(1001)
    at(MIDWINDOW)
    for code in ("12345", "1234567", "12a456", "  1234"):
        with pytest.raises(HTTPException):
            safe.safe_guess(1001, SafeGuessBody(code=code))


def test_the_response_carries_no_clue(db, at):
    _register(1001)
    at(MIDWINDOW)
    _force_secret(SECRET)
    result = safe.safe_guess(1001, SafeGuessBody(code=SECRET))
    assert "exact" not in result and "misplaced" not in result


# ─── Sealed until close ───────────────────────────────────────────────────────


def test_todays_guesses_stay_off_the_board_until_the_window_closes(db, at):
    _register(1001, 1002)
    at(MIDWINDOW)
    _force_secret(SECRET)
    safe.safe_guess(1001, SafeGuessBody(code=NEAR))
    safe.safe_guess(1002, SafeGuessBody(code=SCRAMBLED))

    # Mid-window: a player sees only that their own guesses are locked in.
    state = safe.safe_state(1001)
    assert state["board"] == []
    assert state["pending_codes"] == [NEAR]
    assert state["is_open"] is True

    at(CLOSED)
    state = safe.safe_state(1001)
    assert state["is_open"] is False
    assert state["pending_codes"] == []
    board = {entry["code"]: (entry["exact"], entry["misplaced"]) for entry in state["board"]}
    # Everyone's guesses appear at once, with the clues the other players earned.
    assert board == {NEAR: (3, 0), SCRAMBLED: (0, 6)}


def test_a_late_player_cannot_read_the_board_before_guessing(db, at):
    _register(1001, 1002)
    at(MIDWINDOW)
    _force_secret(SECRET)
    safe.safe_guess(1001, SafeGuessBody(code=SECRET))
    assert safe.safe_state(1002)["board"] == []


# ─── Rounds ───────────────────────────────────────────────────────────────────


def test_an_uncracked_code_survives_to_the_next_day(db, at):
    _register(1001)
    at(MIDWINDOW)
    _force_secret(SECRET)
    safe.safe_guess(1001, SafeGuessBody(code=MISS))

    at(CLOSED)
    with get_session() as session:
        assert safe.resolve_due_days(session, CLOSED) is None
        session.commit()

    at(NEXT_DAY)
    state = safe.safe_state(1001)
    # Same secret, and yesterday's guess is still on the board to reason from.
    assert _secret() == SECRET
    assert [entry["code"] for entry in state["board"]] == [MISS]
    assert state["attempts_left"] == 3


def test_cracking_the_code_pays_half_the_treasury_and_starts_a_new_round(db, at):
    _register(1001)
    _fill_treasury(1000)
    before = _usd(1001)
    at(MIDWINDOW)
    _force_secret(SECRET)
    safe.safe_guess(1001, SafeGuessBody(code=SECRET))

    at(CLOSED)
    with get_session() as session:
        result = safe.resolve_due_days(session, CLOSED)
        session.commit()

    assert result["prize_usd"] == 500
    assert result["secret"] == SECRET
    assert [payout["usd"] for payout in result["payouts"]] == [500]

    assert _usd(1001) - before == 500
    with get_session() as session:
        assert ledger.treasury_balance(session, "usd") == 500

    at(NEXT_DAY)
    safe.safe_state(1001)
    assert _secret() != SECRET


def test_losing_the_race_to_open_a_round_returns_the_winner_s_round(db, at, monkeypatch):
    """Two players opening the safe at 19:00:00 both try to create the day's round. The
    loser must come back with the round that won, not with "сейф недоступен" — which is
    what happened on production the first time two sessions collided."""
    now = MIDWINDOW
    with get_session() as session:
        winner_id = safe.current_round(session, now).id
        session.commit()

    # SQLite does not reproduce MySQL's REPEATABLE READ, so the loser's blind spot is
    # simulated: its first two reads see nothing, while the unique index — which is never
    # snapshotted — still rejects the insert. That is exactly the shape of the production
    # failure, and it drives the code down the recovery branch.
    blind = {"reads": 2}
    real_scalar, real_scalars = Session.scalar, Session.scalars

    class _NothingFound:
        def first(self):
            return None

    def blind_scalar(self, *args, **kwargs):
        if blind["reads"] > 0:
            blind["reads"] -= 1
            return None
        return real_scalar(self, *args, **kwargs)

    def blind_scalars(self, *args, **kwargs):
        if blind["reads"] > 0:
            blind["reads"] -= 1
            return _NothingFound()
        return real_scalars(self, *args, **kwargs)

    monkeypatch.setattr(Session, "scalar", blind_scalar)
    monkeypatch.setattr(Session, "scalars", blind_scalars)

    with get_session() as session:
        recovered = safe.current_round(session, now)

    assert blind["reads"] == 0, "the blind reads must actually have been consumed"
    assert recovered is not None, "the loser must not be told the safe is unavailable"
    assert recovered.id == winner_id, "the loser must get the round that won, not a second one"


def test_the_replacement_round_never_reuses_the_cracked_code(db, at):
    """A round cracked the same evening it opened must not hand its own row back."""
    _register(1001)
    _fill_treasury(1000)
    at(MIDWINDOW)
    _force_secret(SECRET)
    safe.safe_guess(1001, SafeGuessBody(code=SECRET))

    at(CLOSED)
    with get_session() as session:
        safe.resolve_due_days(session, CLOSED)
        session.commit()

    # Straight after the reveal, still inside the same Moscow period.
    with get_session() as session:
        fresh = safe.current_round(session, CLOSED)
        session.commit()
        assert fresh.solved_at is None
        assert fresh.opened_on == DAY + timedelta(days=1)

    assert _secret() != SECRET
    assert safe.safe_state(1001)["board"] == [], "the new round starts on a clean board"


def test_a_tie_splits_the_prize_evenly(db, at):
    _register(1001, 1002)
    _fill_treasury(1000)
    at(MIDWINDOW)
    _force_secret(SECRET)
    safe.safe_guess(1001, SafeGuessBody(code=SECRET))
    safe.safe_guess(1002, SafeGuessBody(code=SECRET))

    at(CLOSED)
    with get_session() as session:
        result = safe.resolve_due_days(session, CLOSED)
        session.commit()

    assert [payout["usd"] for payout in result["payouts"]] == [250, 250]
    with get_session() as session:
        # 500 left plus the odd dollar that no split could reach.
        assert ledger.treasury_balance(session, "usd") == 500


def test_resolving_twice_pays_once(db, at):
    _register(1001)
    _fill_treasury(1000)
    before = _usd(1001)
    at(MIDWINDOW)
    _force_secret(SECRET)
    safe.safe_guess(1001, SafeGuessBody(code=SECRET))

    at(CLOSED)
    with get_session() as session:
        safe.resolve_due_days(session, CLOSED)
        session.commit()
    with get_session() as session:
        assert safe.resolve_due_days(session, CLOSED) is None
        session.commit()

    assert _usd(1001) - before == 500
    with get_session() as session:
        assert ledger.treasury_balance(session, "usd") == 500


def test_an_empty_treasury_pays_nothing_and_still_ends_the_round(db, at):
    _register(1001)
    at(MIDWINDOW)
    _force_secret(SECRET)
    safe.safe_guess(1001, SafeGuessBody(code=SECRET))

    at(CLOSED)
    with get_session() as session:
        result = safe.resolve_due_days(session, CLOSED)
        session.commit()

    assert result["prize_usd"] == 0
    with get_session() as session:
        assert session.query(SafeRound).one().solved_at is not None


def test_the_payout_reconciles_with_the_ledger(db, at):
    _register(1001, 1002)
    _fill_treasury(777)
    before = _usd(1001)
    at(MIDWINDOW)
    _force_secret(SECRET)
    safe.safe_guess(1001, SafeGuessBody(code=SECRET))

    at(CLOSED)
    with get_session() as session:
        safe.resolve_due_days(session, CLOSED)
        session.commit()

    with get_session() as session:
        player = session.query(Player).filter_by(telegram_id=1001).one()
        entries = session.query(LedgerEntry).filter_by(player_id=player.id, currency="usd").all()
        assert sum(entry.delta for entry in entries) == player.balance_usd
        assert [entry.reason for entry in entries if entry.reason == "safe_prize"] == ["safe_prize"]
        # Every dollar that left the treasury landed on a balance — 777 splits into a
        # 388 prize and the 389 that stays behind for the next round.
        assert player.balance_usd - before == 388
        assert ledger.treasury_balance(session, "usd") == 389


def test_the_payout_is_journalled_against_the_round(db, at):
    """Every dollar leaving the house leaves a row saying which round took it."""
    _register(1001)
    _fill_treasury(1000)
    at(MIDWINDOW)
    _force_secret(SECRET)
    safe.safe_guess(1001, SafeGuessBody(code=SECRET))

    at(CLOSED)
    with get_session() as session:
        result = safe.resolve_due_days(session, CLOSED)
        session.commit()

    with get_session() as session:
        total, stored = ledger.reconcile_treasury(session, "usd")
        assert total == stored == 500
        payout = (
            session.query(TreasuryLedgerEntry)
            .filter_by(reason="safe_prize")
            .order_by(TreasuryLedgerEntry.id.desc())
            .first()
        )
        assert payout.delta == -500
        assert (payout.ref_table, payout.ref_id) == ("safe_rounds", result["round_id"])


def test_an_earlier_day_wins_before_a_later_one(db, at):
    """A worker that was down for a day still pays the day the code actually fell."""
    _register(1001, 1002)
    _fill_treasury(1000)
    at(MIDWINDOW)
    _force_secret(SECRET)
    safe.safe_guess(1001, SafeGuessBody(code=SECRET))

    # A second crack lands the following evening, before anything was resolved.
    at(NEXT_DAY)
    safe.safe_guess(1002, SafeGuessBody(code=SECRET))

    later = NEXT_DAY + timedelta(hours=4)
    with get_session() as session:
        result = safe.resolve_due_days(session, later)
        session.commit()

    assert [payout["player_id"] for payout in result["payouts"]] == [
        _player_id(1001)
    ], "the first day to close must decide the round"


def _player_id(telegram_id: int) -> int:
    with get_session() as session:
        return session.query(Player).filter_by(telegram_id=telegram_id).one().id


def test_guesses_are_attributed_to_the_window_not_the_calendar_date(db, at):
    """A guess at 22:59 and one at 19:01 belong to the same reveal."""
    _register(1001)
    late = OPEN + timedelta(hours=3, minutes=59)
    at(late)
    safe.safe_guess(1001, SafeGuessBody(code=MISS))
    with get_session() as session:
        assert session.query(SafeAttempt).one().day == DAY
