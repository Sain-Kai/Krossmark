import numpy as np


class EvidenceAccumulator:
    def __init__(self, window=30, threshold=0.6):
        """
        window: How many VLM results to keep in memory for voting.
        threshold: The percentage (0.0 to 1.0) of 'weapon' detections 
                   needed to trigger a confirmation.
        """
        # stores {track_id: [list of recent VLM weapon labels]}
        self.history = {}

        # stores {track_id: {"weapon": "pistol", "confirmed": True}}
        self.state = {}

        self.window = window
        self.threshold = threshold

    def update(self, track_id, vlm_parsed_json):
        """
        Processes a new JSON result from the VLM.
        Example input: {"weapon": "pistol", "confidence": "high"}
        """
        if track_id not in self.history:
            self.history[track_id] = []

        label = vlm_parsed_json.get("weapon", "none").lower()

        # Add to rolling window
        self.history[track_id].append(label)
        if len(self.history[track_id]) > self.window:
            self.history[track_id].pop(0)

        # Re-calculate state for this track
        self._calculate_state(track_id)

    def _calculate_state(self, track_id):
        """Internal logic to vote on the most likely weapon state."""
        hist = self.history.get(track_id, [])
        if not hist:
            return

        # Count occurrences of non-'none' labels
        weapon_hits = [h for h in hist if h not in ["none", "unknown", "nothing"]]

        if not weapon_hits:
            self.state[track_id] = {"weapon": "none", "confirmed": False}
            return

        # Find the most frequent weapon label
        most_common = max(set(weapon_hits), key=weapon_hits.count)
        hit_ratio = len(weapon_hits) / len(hist)

        # Confirm if it crosses the threshold
        is_confirmed = hit_ratio >= self.threshold

        self.state[track_id] = {
            "weapon": most_common,
            "confirmed": is_confirmed,
            "ratio": round(hit_ratio, 2)
        }

    def get_state(self, track_id):
        """Returns the current consensus for a track."""
        return self.state.get(track_id, {"weapon": "none", "confirmed": False})

    def clear_track(self, track_id):
        """
        Removes evidence for a track that left the scene.
        Essential for memory management and preventing 'ghost' alerts.
        """
        if track_id in self.history:
            del self.history[track_id]
        if track_id in self.state:
            del self.state[track_id]

    def reset(self):
        """Full reset of all accumulated evidence."""
        self.history.clear()
        self.state.clear()