from __future__ import annotations

from enum import Enum


class HabitatType(str, Enum):
    FIELDS = "fields"
    DESERT = "desert"
    FOREST = "forest"
    MOUNTAINS = "mountains"
    ANTARCTICA = "antarctica"


class GeneLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class AnimalStatus(str, Enum):
    ACTIVE = "active"
    ON_EXPEDITION = "on_expedition"
    DEAD = "dead"


class AnimalOriginType(str, Enum):
    PACK = "pack"
    BREEDING = "breeding"
    EXPEDITION = "expedition"


class PackOpeningType(str, Enum):
    FREE = "free"
    PAID = "paid"


class ExpeditionOutcome(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILURE = "failure"
