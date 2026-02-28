from collections import defaultdict
from vision.core.intent.states import PersonIntent

class PersonIntentEngine:
    def __init__(self, persist_frames=30, decay_frames=60):
        self.state = defaultdict(lambda: PersonIntent.IDLE)
        self.counter = defaultdict(int)
        self.persist = persist_frames
        self.decay = decay_frames

    def update(self, track_id, features, weapon_state):
        """
        features: dict with speed, direction, dwell(optional), etc.
        weapon_state: dict or None from EvidenceAccumulator
        """
        cur = self.state[track_id]
        speed = features.get("speed", 0)

        has_weapon = bool(weapon_state and weapon_state.get("confirmed"))
        suspicious_weapon = bool(weapon_state and weapon_state.get("weapon") not in ["none", "unknown", None])

        # Heuristic signals
        fast = speed > 60
        moving = speed > 10

        # Propose next state
        proposed = cur

        if has_weapon and fast:
            proposed = PersonIntent.ATTACKING
        elif has_weapon:
            proposed = PersonIntent.AGGRESSIVE
        elif suspicious_weapon:
            proposed = PersonIntent.SCOUTING
        elif moving:
            proposed = PersonIntent.OBSERVING
        else:
            proposed = PersonIntent.IDLE

        # Persistence logic
        if proposed == cur:
            self.counter[track_id] = min(self.counter[track_id] + 1, self.persist)
        else:
            self.counter[track_id] -= 1
            if self.counter[track_id] <= 0:
                self.state[track_id] = proposed
                self.counter[track_id] = self.persist // 2

        # Decay back to safer state
        if cur in [PersonIntent.AGGRESSIVE, PersonIntent.ATTACKING] and not has_weapon:
            self.counter[track_id] -= 2
            if self.counter[track_id] <= -self.decay:
                self.state[track_id] = PersonIntent.OBSERVING
                self.counter[track_id] = 0

        return self.state[track_id]