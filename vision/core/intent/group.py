from collections import deque
from vision.core.intent.states import GroupIntent

class GroupIntentEngine:
    def __init__(self, window=10):
        self.history = deque(maxlen=window)

    def update(self, groups):
        """
        groups: output of group_tracks(tracks)
        """
        if not groups or len(groups) <= 1:
            self.history.append(GroupIntent.NONE)
        else:
            # If any group has size >= 3 → coordinated
            big = any(len(g) >= 3 for g in groups)
            if big:
                self.history.append(GroupIntent.COORDINATED)
            else:
                self.history.append(GroupIntent.LOOSE)

        # Majority vote over window
        counts = {}
        for g in self.history:
            counts[g] = counts.get(g, 0) + 1

        return max(counts, key=counts.get)