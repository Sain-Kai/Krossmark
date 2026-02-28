from collections import deque

class SceneStabilizer:
    def __init__(self, window=10, hysteresis=2):
        self.window = window
        self.hysteresis = hysteresis
        self.scene_hist = deque(maxlen=window)
        self.threat_hist = deque(maxlen=window)
        self.last_scene = None
        self.last_threat = None

    def _majority(self, arr):
        counts = {}
        for x in arr:
            counts[x] = counts.get(x, 0) + 1
        return max(counts, key=counts.get)

    def update(self, scene_intent, threat_level):
        self.scene_hist.append(scene_intent)
        self.threat_hist.append(threat_level)

        scene_maj = self._majority(self.scene_hist)
        threat_avg = int(round(sum(self.threat_hist) / len(self.threat_hist)))

        # Hysteresis: don’t change unless stable enough
        if self.last_scene is None:
            self.last_scene = scene_maj
        else:
            if scene_maj != self.last_scene:
                if list(self.scene_hist).count(scene_maj) >= self.hysteresis:
                    self.last_scene = scene_maj

        if self.last_threat is None:
            self.last_threat = threat_avg
        else:
            if abs(threat_avg - self.last_threat) >= 1:
                if list(self.threat_hist).count(threat_avg) >= self.hysteresis:
                    self.last_threat = threat_avg

        return self.last_scene, self.last_threat