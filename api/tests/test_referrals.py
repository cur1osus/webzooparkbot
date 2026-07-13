from sqlalchemy import select

from api.app.db.connection import get_session
from api.app.db.models import LedgerEntry, Player
from api.app.schemas.core import RegisterBody
from api.app.schemas.economy import BankExchangeBody
from api.app.zoopark import economy, ledger
from api.app.zoopark.catalog import REFERRAL_NEW_PLAYER_REWARD_USD, REFERRAL_SIGNUP_REWARD_USD
from api.app.zoopark.core import register


def test_startapp_referral_code_links_new_player_and_rewards_inviter(db):
    register(1001, RegisterBody(nickname="inviter"))
    register(2002, RegisterBody(nickname="new-player", ref_code="1001"))

    with get_session() as session:
        inviter = session.scalar(select(Player).where(Player.telegram_id == 1001))
        referred = session.scalar(select(Player).where(Player.telegram_id == 2002))
        assert inviter is not None
        assert referred is not None
        assert referred.referred_by_id == inviter.id
        assert inviter.balance_usd == 1 + REFERRAL_SIGNUP_REWARD_USD
        assert referred.balance_usd == REFERRAL_NEW_PLAYER_REWARD_USD

        reward = session.scalar(
            select(LedgerEntry).where(
                LedgerEntry.player_id == inviter.id,
                LedgerEntry.reason == "referral_signup",
            )
        )
        assert reward is not None
        assert reward.delta == REFERRAL_SIGNUP_REWARD_USD


def test_invalid_referral_code_keeps_standard_signup_reward(db):
    register(3003, RegisterBody(nickname="ordinary-player", ref_code="999999"))

    with get_session() as session:
        player = session.scalar(select(Player).where(Player.telegram_id == 3003))
        assert player is not None
        assert player.balance_usd == 1


def test_referral_exchange_gets_five_percent_of_post_fee_usd(db):
    register(4004, RegisterBody(nickname="exchange-inviter"))
    register(5005, RegisterBody(nickname="exchange-referral", ref_code="4004"))

    with get_session() as session:
        referred = session.scalar(select(Player).where(Player.telegram_id == 5005))
        assert referred is not None
        rate = economy.base_rate(session, now=None)
        ledger.grant(session, referred, "rub", rate * 1_000, "daily_bonus")
        session.commit()

    result = economy.exchange(5005, BankExchangeBody(amount_rub=rate * 1_000))

    with get_session() as session:
        inviter = session.scalar(select(Player).where(Player.telegram_id == 4004))
        assert inviter is not None
        assert result["fee_usd"] == 30
        assert result["referrer_usd"] == 48
        assert result["received_usd"] == 922
        assert inviter.balance_usd == 1 + REFERRAL_SIGNUP_REWARD_USD + 48
