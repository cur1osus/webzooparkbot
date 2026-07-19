"""MCP server exposing the rivals' toolset, so a human can drive or inspect a bot by hand.

Same `tools.REGISTRY` the agent uses — this file adds a protocol, never a second copy of a
game action. Anything you do through here is exactly what the bot does through the loop.

The agent itself does *not* speak MCP to reach these tools: it dispatches to the registry
in-process, because a protocol hop to your own function would buy nothing. This server is
for everything else — pointing an MCP client at a bot to watch what it sees, reproducing a
bad turn move by move, or playing a rival manually.

    ANTHROPIC_BOT_TG_ID=-1002 python -m api.bots.mcp_server

Speaks JSON-RPC 2.0 over stdio (`initialize`, `tools/list`, `tools/call`), which is what an
MCP client expects. Deliberately dependency-free: the protocol surface needed here is small,
and adding an SDK to `requirements.txt` for it would put a new package in the API's
virtualenv for the sake of three message types.
"""

from __future__ import annotations

import json
import logging
import os
import sys

from sqlalchemy import select

from api.app.db.connection import get_session
from api.app.db.models import Player
from api.bots import tools

logger = logging.getLogger(__name__)

PROTOCOL_VERSION = "2024-11-05"


def _resolve_bot(tg_id: int) -> tuple[int, int, str]:
    """(tg_id, player_id, nickname) for a bot account. Refuses anything that is not one, so
    this server can never be pointed at a real player's zoo."""
    with get_session() as session:
        player = session.scalar(select(Player).where(Player.telegram_id == tg_id))
        if player is None:
            raise SystemExit(f"нет игрока с telegram_id={tg_id}")
        if not player.is_bot:
            raise SystemExit(f"игрок {player.nickname} — не бот; этот сервер работает только с ботами")
        return int(player.telegram_id), int(player.id), player.nickname


def _respond(message_id, result=None, error=None) -> None:
    payload = {"jsonrpc": "2.0", "id": message_id}
    if error is not None:
        payload["error"] = error
    else:
        payload["result"] = result
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _tool_list() -> dict:
    return {
        "tools": [
            {
                "name": entry.name,
                "description": entry.description,
                "inputSchema": {
                    "type": "object",
                    "properties": entry.properties,
                    "required": entry.required,
                },
            }
            for entry in tools.REGISTRY.values()
        ]
    }


def serve(tg_id: int, player_id: int, nickname: str) -> None:
    logger.info("MCP server for %s (tg_id=%s), %s tools", nickname, tg_id, len(tools.REGISTRY))
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            continue

        method = message.get("method")
        message_id = message.get("id")

        if method == "initialize":
            _respond(message_id, {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": {"name": f"zoopark-bot:{nickname}", "version": "1.0.0"},
            })
        elif method == "notifications/initialized":
            continue  # a notification carries no id and expects no reply
        elif method == "tools/list":
            _respond(message_id, _tool_list())
        elif method == "tools/call":
            params = message.get("params") or {}
            name = params.get("name") or ""
            arguments = params.get("arguments") or {}
            output = tools.call(name, tg_id, player_id, arguments)
            _respond(message_id, {
                "content": [{"type": "text", "text": json.dumps(output, ensure_ascii=False, default=str)}],
                "isError": not output.get("ok", True),
            })
        elif message_id is not None:
            _respond(message_id, error={"code": -32601, "message": f"неизвестный метод: {method}"})


def main() -> None:
    logging.basicConfig(level=logging.INFO, stream=sys.stderr,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    raw = os.getenv("BOT_TG_ID")
    if not raw:
        raise SystemExit("укажи BOT_TG_ID — telegram_id бота, например -1002")
    serve(*_resolve_bot(int(raw)))


if __name__ == "__main__":
    main()
