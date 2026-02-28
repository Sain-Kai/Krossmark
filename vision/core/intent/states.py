from enum import Enum

class PersonIntent(str, Enum):
    IDLE = "idle"
    OBSERVING = "observing"
    LOITERING = "loitering"
    SCOUTING = "scouting"
    AGGRESSIVE = "aggressive"
    ATTACKING = "attacking"
    UNKNOWN = "unknown"

class GroupIntent(str, Enum):
    NONE = "none"
    LOOSE = "loose_group"
    COORDINATED = "coordinated"
    SURROUNDING = "surrounding"

class SceneIntent(str, Enum):
    NORMAL = "normal"
    SUSPICIOUS = "suspicious"
    PREPARATION = "preparation"
    ATTACK = "attack"