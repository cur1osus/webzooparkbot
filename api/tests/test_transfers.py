from sqlalchemy import select

from api.app.db.connection import get_session
from api.app.db.models import Player
from api.app.schemas.core import RegisterBody
from api.app.schemas.social import TransferCreateBody
from api.app.zoopark.core import register
from api.app.zoopark.social import transfer_claim, transfers_create


def test_transfer_claim_credits_recipient_once(db, grant):
    register(1001, RegisterBody(nickname="sender"))
    register(2002, RegisterBody(nickname="recipient"))
    grant(1001, "rub", 100)

    created = transfers_create(1001, TransferCreateBody(total_rub=50, max_claims=2))
    claimed = transfer_claim(2002, created["code"])

    assert claimed["rub_received"] == 25
    assert claimed["new_rub"] == 25

    with get_session() as session:
        recipient = session.scalar(select(Player).where(Player.telegram_id == 2002))
        assert recipient is not None
        assert recipient.balance_rub == 25


def test_dollar_transfer_debits_and_credits_dollars(db, grant):
    register(3003, RegisterBody(nickname="dollar sender"))
    register(4004, RegisterBody(nickname="dollar recipient"))
    grant(3003, "usd", 100)

    created = transfers_create(3003, TransferCreateBody(total_rub=50, max_claims=2, currency="usd"))
    claimed = transfer_claim(4004, created["code"])

    assert created["currency"] == "usd"
    assert created["new_usd"] == 51
    assert claimed["currency"] == "usd"
    assert claimed["amount_received"] == 25
    assert claimed["new_usd"] == 26

    with get_session() as session:
        recipient = session.scalar(select(Player).where(Player.telegram_id == 4004))
        assert recipient is not None
        assert recipient.balance_usd == 26
