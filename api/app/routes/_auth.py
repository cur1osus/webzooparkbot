"""Shared auth dependency.

Every route used to repeat `x_init_data: str = Header(default="")` and
`x_dev_user_id: str = Header(default="")` and then call `auth(...)` by hand. One
dependency means one place where a route can forget to authenticate.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header

from api.app.core.auth import auth


def _current_player(
    x_init_data: str = Header(default=""),
    x_dev_user_id: str = Header(default=""),
) -> int:
    return auth(x_init_data, x_dev_user_id)


TelegramId = Annotated[int, Depends(_current_player)]
