"""Player-wide development tracks used by the Zoo's Development tab."""

from __future__ import annotations

from fastapi import HTTPException

from api.app.db.connection import get_session
from api.app.schemas.development import UpgradeDevelopmentBody
from api.app.zoopark import ledger
from api.app.zoopark.catalog import (
    DEVELOPMENT_MAX_LEVEL,
    development_upgrade_cost_rub,
)
from api.app.zoopark.profile import get_player


_LEVEL_FIELD = {"vet": "vet_level", "genetics": "genetics_level", "expedition": "expedition_level"}


def upgrade(tg_id: int, body: UpgradeDevelopmentBody) -> dict:
    with get_session() as session:
        player = get_player(session, tg_id, for_update=True)
        if not player:
            raise HTTPException(404, "Нет игрока")
        field = _LEVEL_FIELD[body.kind]
        level = int(getattr(player, field))
        cost = development_upgrade_cost_rub(body.kind, level)
        if cost is None or level >= DEVELOPMENT_MAX_LEVEL:
            raise HTTPException(400, "Улучшение уже достигло максимального уровня")
        ledger.spend(session, player, "rub", cost, "development_upgrade")
        setattr(player, field, level + 1)
        session.commit()
        return {
            "ok": True,
            "kind": body.kind,
            "level": level + 1,
            "next_cost_rub": development_upgrade_cost_rub(body.kind, level + 1),
            "new_rub": ledger.balance(player, "rub"),
        }
