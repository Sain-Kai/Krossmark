# vision/core/features/motion.py

import math


def compute_speed(history):
    """
    Computes average translational speed (pixels per frame)
    history: [(cx, cy, frame_idx), ...]
    """

    if len(history) < 2:
        return 0.0

    speeds = []

    for i in range(1, len(history)):
        x1, y1, f1 = history[i - 1]
        x2, y2, f2 = history[i]

        dt = max(1, f2 - f1)

        dx = x2 - x1
        dy = y2 - y1

        dist = math.sqrt(dx * dx + dy * dy)

        speeds.append(dist / dt)

    return sum(speeds) / len(speeds)


def compute_limb_velocity(pose_flags):
    """
    Computes average wrist movement magnitude (angular motion proxy)
    pose_flags: list of keypoint dicts
    """

    if len(pose_flags) < 2:
        return 0.0

    velocities = []

    for i in range(1, len(pose_flags)):
        prev = pose_flags[i - 1]
        curr = pose_flags[i]

        if "right_wrist" not in prev or "right_wrist" not in curr:
            continue

        dx = curr["right_wrist"][0] - prev["right_wrist"][0]
        dy = curr["right_wrist"][1] - prev["right_wrist"][1]

        velocities.append(math.sqrt(dx * dx + dy * dy))

    if not velocities:
        return 0.0

    return sum(velocities) / len(velocities)