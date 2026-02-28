from vision.core.intent.states import SceneIntent, PersonIntent, GroupIntent

class SceneIntentEngine:
    def update(self, person_intents, group_intent):
        """
        person_intents: list of PersonIntent
        """
        if any(p == PersonIntent.ATTACKING for p in person_intents):
            return SceneIntent.ATTACK
        if any(p == PersonIntent.AGGRESSIVE for p in person_intents) or group_intent == GroupIntent.COORDINATED:
            return SceneIntent.PREPARATION
        if any(p in [PersonIntent.SCOUTING, PersonIntent.OBSERVING] for p in person_intents):
            return SceneIntent.SUSPICIOUS
        return SceneIntent.NORMAL