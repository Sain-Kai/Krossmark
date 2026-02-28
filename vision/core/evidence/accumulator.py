from collections import deque, Counter


class EvidenceAccumulator:
    def __init__(self, window=10, confirm_threshold=0.6):
        self.window = window
        self.th = confirm_threshold
        self.mem = {}  # track_id -> deque

    def get_state(self, track_id):
        """Returns the current aggregated state for a track without updating it."""
        if track_id not in self.mem or not self.mem[track_id]:
            return {"weapon": "none", "score": 0.0, "confirmed": False}

        return self._calculate_state(track_id)

    def update(self, track_id, vlm_result):
        """Adds a new VLM result and returns the updated state."""
        if track_id not in self.mem:
            self.mem[track_id] = deque(maxlen=self.window)

        self.mem[track_id].append(vlm_result)
        return self._calculate_state(track_id)

    def _calculate_state(self, track_id):
        """Internal helper to calculate majority vote."""
        vals = list(self.mem[track_id])
        # Filter out None values in case of failed parses
        weapons = [v.get("weapon", "unknown") for v in vals if v and isinstance(v, dict)]

        if not weapons:
            return {"weapon": "none", "score": 0.0, "confirmed": False}

        cnt = Counter(weapons)
        best, freq = cnt.most_common(1)[0]
        score = freq / len(weapons)

        confirmed = (best not in ["none", "unknown"]) and (score >= self.th)

        return {
            "weapon": best,
            "score": round(score, 2),
            "confirmed": confirmed
        }