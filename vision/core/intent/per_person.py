from collections import defaultdict
from vision.core.intent.states import PersonIntent


class PersonIntentEngine:

    def __init__(self, persist_frames=15, decay_frames=40):
        self.state = defaultdict(lambda: PersonIntent.IDLE)
        self.counter = defaultdict(int)
        self.persist = persist_frames
        self.decay = decay_frames

    def update(self, track_id, features, weapon_state):

        cur = self.state[track_id]

        speed = features.get("speed", 0)
        direction = features.get("direction", (0, 0))
        pose_flags = features.get("pose_flags", [])

        has_weapon = bool(weapon_state and weapon_state.get("confirmed"))
        suspicious_weapon = bool(
            weapon_state and weapon_state.get("weapon") not in ["none", "unknown", None]
        )

        fast = speed > 70
        moving = speed > 15

        # Direction toward border assumed upward (dy < 0)
        approaching_border = direction[1] < -0.3

        # Pose aggression
        aggressive_pose = any(
            p.get("arms_raised") and p.get("reaching_forward")
            for p in pose_flags
        )

        proposed = cur

        if has_weapon and fast:
            proposed = PersonIntent.ATTACKING

        elif has_weapon and aggressive_pose:
            proposed = PersonIntent.AGGRESSIVE

        elif suspicious_weapon:
            proposed = PersonIntent.SCOUTING

        elif approaching_border and moving:
            proposed = PersonIntent.APPROACHING_BORDER

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

        # Decay logic
        if cur in [PersonIntent.AGGRESSIVE, PersonIntent.ATTACKING] and not has_weapon:
            self.counter[track_id] -= 2
            if self.counter[track_id] <= -self.decay:
                self.state[track_id] = PersonIntent.OBSERVING
                self.counter[track_id] = 0

        return self.state[track_id]