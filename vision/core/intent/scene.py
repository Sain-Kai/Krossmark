from vision.core.intent.states import SceneIntent, PersonIntent, GroupIntent


class SceneIntentEngine:

    def update(self, person_intents, group_intent):

        if not person_intents:
            return SceneIntent.NORMAL

        attacking = any(p == PersonIntent.ATTACKING for p in person_intents)
        aggressive = any(p == PersonIntent.AGGRESSIVE for p in person_intents)
        approaching = any(p == PersonIntent.APPROACHING_BORDER for p in person_intents)

        coordinated = group_intent in [
            GroupIntent.COORDINATED,
            GroupIntent.FORMATION_ADVANCE
        ]

        if attacking:
            return SceneIntent.ATTACK

        if aggressive and coordinated:
            return SceneIntent.BREACH_ATTEMPT

        if approaching and coordinated:
            return SceneIntent.PREPARATION

        if aggressive:
            return SceneIntent.SUSPICIOUS

        if all(p in [PersonIntent.IDLE, PersonIntent.OBSERVING] for p in person_intents):
            return SceneIntent.NORMAL

        return SceneIntent.SUSPICIOUS