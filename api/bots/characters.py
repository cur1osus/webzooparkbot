"""Who the AI rivals are.

A character is a temperament, not a strategy. It says what the bot cares about and what it
is willing to risk; it never says which move to make. The moves are the model's own — it
sees the board through the toolset and decides. That inconsistency between turns is the
point: a rival that plays the same optimal line every day reads as a script no matter how
good the line is.

One rival, because each one costs a turn's worth of model calls and one is enough to make
the leaderboard feel occupied. The gambler is the one kept: swings, visible risk, and turns
that read differently from each other. A hoarder compounds quietly and is duller to watch,
which is the opposite of the point.

The name comes from the same era as the game's animal names (Леонардо, Боттичелли, Медичи —
see `ANIMAL_NAME_POOL`) but deliberately *not from that list*, so a player never confuses the
rival with somebody's parrot. Sforza were the Milanese house that rivalled the Medici, and
condottieri who gambled their way to a duchy — which is the temperament below.

No avatar field: a rival's `profile_emoji` starts NULL like a new player's, so the client
draws it the default animal every account gets, and it earns a real one the way a human does
— by unlocking an achievement and putting it on with `set_profile_avatar`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Character:
    key: str
    nickname: str
    # Second person, present tense: it goes into the opening message as "you are this".
    temperament: str
    # Waking window in UTC. Not a handicap — a rhythm. A rival that plays around the clock
    # out-grows every human by arithmetic alone, and a leaderboard nobody can reach is worse
    # than an empty one. Different windows also mean the two are rarely active at once, so
    # they read as separate people.
    wake_hour_utc: int
    sleep_hour_utc: int
    # How often it takes a turn. Each turn is one agent loop, and that is what costs money.
    turn_every_minutes: int


CHARACTERS: dict[str, Character] = {
    "gambler": Character(
        key="gambler",
        nickname="Сфорца",
        temperament=(
            "Ты играешь на рывок. Тебе скучно расти на процент в час — ты хочешь поймать "
            "легендарного зверя и прыгнуть через полтопа за раз. Паки, глубокие экспедиции "
            "и дуэли — твоя стихия. Проигрыш тебя заводит сильнее, чем выигрыш: после "
            "провала тянет отыграться. Иногда ты остаёшься без денег и вынужден "
            "отсиживаться, и это тебя бесит."
        ),
        wake_hour_utc=11,
        sleep_hour_utc=2,
        turn_every_minutes=45,
    ),
}


def get(key: str) -> Character:
    try:
        return CHARACTERS[key]
    except KeyError:
        raise ValueError(f"unknown character {key!r}; known: {sorted(CHARACTERS)}") from None
