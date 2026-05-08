from collections import deque
from vision.core.intent.states import GroupIntent


class GroupIntentEngine:

    def __init__(self, window=8):
        self.history = deque(maxlen=window)

    def update(self, groups):

        if not groups or len(groups) <= 1:
            self.history.append(GroupIntent.NONE)

        else:
            large_group = any(len(g) >= 3 for g in groups)

            if large_group:
                self.history.append(GroupIntent.COORDINATED)
            elif len(groups) >= 2:
                self.history.append(GroupIntent.LOOSE)
            else:
                self.history.append(GroupIntent.NONE)

        # Majority vote
        counts = {}
        for g in self.history:
            counts[g] = counts.get(g, 0) + 1

        return max(counts, key=counts.get)