class VLMScheduler:
    def __init__(self, cooldown_frames=120):
        self.cooldown = cooldown_frames
        self.last_called = {}

    def should_call(self, track_id, frame_idx, threat_level, ambiguous=False):
        last = self.last_called.get(track_id, -10**9)

        if frame_idx - last < self.cooldown:
            return False

        # Only escalate to VLM if:
        # - ambiguous AND
        # - threat is not trivial
        if ambiguous and threat_level >= 2:
            self.last_called[track_id] = frame_idx
            return True

        return False