import math

def compute_speed(track):
    if len(track.history) < 2:
        return 0.0
    (x1, y1, t1) = track.history[-2]
    (x2, y2, t2) = track.history[-1]
    dt = max(t2 - t1, 1e-3)
    dist = math.hypot(x2 - x1, y2 - y1)
    return dist / dt

def compute_direction(track):
    if len(track.history) < 2:
        return (0.0, 0.0)
    (x1, y1, _) = track.history[-2]
    (x2, y2, _) = track.history[-1]
    dx = x2 - x1
    dy = y2 - y1
    norm = math.hypot(dx, dy) + 1e-6
    return (dx / norm, dy / norm)