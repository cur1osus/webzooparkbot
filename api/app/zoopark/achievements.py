"""Lifetime achievement progress for the medals tab.

Achievements are derived from the event tables that already record the game's important
actions. There is no second counter to keep in sync, and progress never goes backwards
when an animal dies or an item is sold.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from api.app.db.models import (
    Animal,
    BreedingAttempt,
    CocktailSolve,
    CustomAchievement,
    CustomAchievementRecipient,
    Expedition,
    LedgerEntry,
    Locality,
    Player,
)


@dataclass(frozen=True)
class AchievementDefinition:
    id: str
    title: str
    description: str
    target: int


ACHIEVEMENTS: tuple[AchievementDefinition, ...] = (
    AchievementDefinition("first_beast", "Первый зверь", "Заведи первое животное в зоопарке", 1),
    AchievementDefinition("growing_zoo", "Зоопарк растёт", "Заведи 10 животных за всё время", 10),
    AchievementDefinition("collector", "Коллекционер", "Собери животных пяти разных видов", 5),
    AchievementDefinition("first_baby", "Первый детёныш", "Получи первого детёныша при скрещивании", 1),
    AchievementDefinition("geneticist", "Генетический фонд", "Успешно проведи 10 скрещиваний", 10),
    AchievementDefinition("first_expedition", "Первый поход", "Одержи первую победу в экспедиции", 1),
    AchievementDefinition("pathfinder", "Покоритель дикой природы", "Победи в пяти экспедициях", 5),
    AchievementDefinition("architect", "Архитектор", "Открой три местности в зоопарке", 3),
    AchievementDefinition("blacksmith", "Кузнец", "Создай три артефакта в кузнице", 3),
    AchievementDefinition("arena_winner", "Мастер коктейля", "Разгадай пять коктейлей дня", 5),
    AchievementDefinition("endgame_zoo", "Великий зверинец", "Собери финальный зверинец из 30 животных", 30),
    AchievementDefinition("endgame_collector", "Хранитель коллекции", "Собери животных 15 разных видов", 15),
    AchievementDefinition("endgame_geneticist", "Мастер наследия", "Стань мастером наследия: 25 успешных скрещиваний", 25),
    AchievementDefinition("endgame_explorer", "Повелитель экспедиций", "Одержи 12 побед в экспедициях", 12),
    AchievementDefinition("endgame_empire", "Империя зоопарков", "Развивай инфраструктуру до 15 уровней суммарно", 15),
)


def list_achievements(session: Session, player: Player) -> list[dict]:
    """Return every medal in a stable order, including incomplete progress."""

    player_id = player.id
    animal_count = int(session.scalar(select(func.count(Animal.id)).where(Animal.player_id == player_id)) or 0)
    species_count = int(
        session.scalar(
            select(func.count(func.distinct(Animal.species_id))).where(Animal.player_id == player_id)
        )
        or 0
    )
    successful_breedings = int(
        session.scalar(
            select(func.count(BreedingAttempt.id)).where(
                BreedingAttempt.player_id == player_id,
                BreedingAttempt.succeeded.is_(True),
            )
        )
        or 0
    )
    expedition_victories = int(
        session.scalar(
            select(func.count(Expedition.id)).where(
                Expedition.player_id == player_id,
                Expedition.outcome == "victory",
            )
        )
        or 0
    )
    locality_count = int(session.scalar(select(func.count(Locality.id)).where(Locality.player_id == player_id)) or 0)
    locality_levels = int(
        session.scalar(select(func.coalesce(func.sum(Locality.level), 0)).where(Locality.player_id == player_id)) or 0
    )
    forge_creations = int(
        session.scalar(
            select(func.count(LedgerEntry.id)).where(
                LedgerEntry.player_id == player_id,
                LedgerEntry.reason == "forge_create",
            )
        )
        or 0
    )
    cocktails_solved = int(
        session.scalar(select(func.count(CocktailSolve.id)).where(CocktailSolve.player_id == player_id)) or 0
    )

    values = {
        "first_beast": animal_count,
        "growing_zoo": animal_count,
        "collector": species_count,
        "first_baby": successful_breedings,
        "geneticist": successful_breedings,
        "first_expedition": expedition_victories,
        "pathfinder": expedition_victories,
        "architect": locality_count,
        "blacksmith": forge_creations,
        "arena_winner": cocktails_solved,
        "endgame_zoo": animal_count,
        "endgame_collector": species_count,
        "endgame_geneticist": successful_breedings,
        "endgame_explorer": expedition_victories,
        "endgame_empire": locality_levels,
    }

    return [
        {
            "id": definition.id,
            "title": definition.title,
            "description": definition.description,
            "value": min(values[definition.id], definition.target),
            "target": definition.target,
            "completed": values[definition.id] >= definition.target,
            "image_url": None,
        }
        for definition in ACHIEVEMENTS
    ] + _custom_achievements(session, player.id)


def _custom_achievements(session: Session, player_id: int) -> list[dict]:
    recipient_ids = set(
        session.scalars(
            select(CustomAchievementRecipient.achievement_id).where(
                CustomAchievementRecipient.player_id == player_id
            )
        ).all()
    )
    rows = session.execute(
        select(
            CustomAchievement.id,
            CustomAchievement.title,
            CustomAchievement.description,
            CustomAchievement.audience,
        ).order_by(CustomAchievement.created_at.asc(), CustomAchievement.id.asc())
    ).all()
    result = []
    for achievement_id, title, description, audience in rows:
        completed = audience == "all" or achievement_id in recipient_ids
        result.append(
            {
                "id": achievement_id,
                "title": title,
                "description": description,
                "value": 1 if completed else 0,
                "target": 1,
                "completed": completed,
                "image_url": f"/api/achievements/{achievement_id}/image",
            }
        )
    return result


def is_known_achievement(session: Session, achievement_id: str) -> bool:
    return achievement_id in {item.id for item in ACHIEVEMENTS} or session.get(CustomAchievement, achievement_id) is not None
