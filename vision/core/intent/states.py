from enum import Enum


class PersonIntent(str, Enum):
    IDLE = "idle"
    OBSERVING = "observing"
    LOITERING = "loitering"
    SCOUTING = "scouting"
    APPROACHING_BORDER = "approaching_border"
    AGGRESSIVE = "aggressive"
    ATTACKING = "attacking"
    RETREATING = "retreating"
    UNKNOWN = "unknown"


class GroupIntent(str, Enum):
    NONE = "none"
    LOOSE = "loose_group"
    COORDINATED = "coordinated"
    SURROUNDING = "surrounding"
    FORMATION_ADVANCE = "formation_advance"


class SceneIntent(str, Enum):
    NORMAL = "normal"
    SUSPICIOUS = "suspicious"
    PREPARATION = "preparation"
    BREACH_ATTEMPT = "breach_attempt"
    ATTACK = "attack"