import numpy as np
from scipy.optimize import linear_sum_assignment
import math
import time

def iou(a, b):
    xA = max(a[0], b[0])
    yA = max(a[1], b[1])
    xB = min(a[2], b[2])
    yB = min(a[3], b[3])

    inter = max(0, xB - xA) * max(0, yB - yA)
    areaA = (a[2]-a[0]) * (a[3]-a[1])
    areaB = (b[2]-b[0]) * (b[3]-b[1])
    union = areaA + areaB - inter + 1e-6
    return inter / union

class Track:
    def __init__(self, track_id, bbox):
        self.id = track_id
        self.bbox = bbox
        self.hits = 1
        self.age = 0
        self.last_seen = time.time()
        self.history = []

    def update(self, bbox):
        self.bbox = bbox
        self.hits += 1
        self.age = 0
        self.last_seen = time.time()
        cx = (bbox[0] + bbox[2]) / 2
        cy = (bbox[1] + bbox[3]) / 2
        self.history.append((cx, cy, time.time()))

class SimpleTracker:
    def __init__(self, iou_threshold=0.3, max_age=30):
        self.iou_threshold = iou_threshold
        self.max_age = max_age
        self.tracks = []
        self.next_id = 1

    def update(self, detections):
        det_bboxes = [d["bbox"] for d in detections]

        if len(self.tracks) == 0:
            for b in det_bboxes:
                self.tracks.append(Track(self.next_id, b))
                self.next_id += 1
            return self.tracks

        cost = np.zeros((len(self.tracks), len(det_bboxes)), dtype=np.float32)

        for i, t in enumerate(self.tracks):
            for j, b in enumerate(det_bboxes):
                cost[i, j] = 1 - iou(t.bbox, b)

        row_ind, col_ind = linear_sum_assignment(cost)

        assigned_tracks = set()
        assigned_dets = set()

        for r, c in zip(row_ind, col_ind):
            if 1 - cost[r, c] >= self.iou_threshold:
                self.tracks[r].update(det_bboxes[c])
                assigned_tracks.add(r)
                assigned_dets.add(c)

        # Unassigned detections → new tracks
        for j, b in enumerate(det_bboxes):
            if j not in assigned_dets:
                self.tracks.append(Track(self.next_id, b))
                self.next_id += 1

        # Age tracks
        alive = []
        for i, t in enumerate(self.tracks):
            if i not in assigned_tracks:
                t.age += 1
            if t.age <= self.max_age:
                alive.append(t)

        self.tracks = alive
        return self.tracks