from sqlalchemy import select

from api.app.db.connection import get_session
from api.app.db.models import LedgerEntry, Player
from api.app.schemas.core import RegisterBody
from api.app.zoopark.catalog import REFERRAL_SIGNUP_REWARD_USD
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

        reward = session.scalar(
            select(LedgerEntry).where(
                LedgerEntry.player_id == inviter.id,
                LedgerEntry.reason == "referral_signup",
            )
        )
        assert reward is not None
        assert reward.delta == REFERRAL_SIGNUP_REWARD_USD
