import numpy as np

# COCO keypoints indices (YOLO format usually follows COCO)
NOSE = 0
LEFT_SHOULDER = 5
RIGHT_SHOULDER = 6
LEFT_HIP = 11
RIGHT_HIP = 12
LEFT_WRIST = 9
RIGHT_WRIST = 10

def posture_from_keypoints(kpts):
    """
    kpts: (K, 2) array or None
    Returns: dict of posture features
    """
    if kpts is None:
        return {
            "crouching": False,
            "arms_raised": False,
            "reaching_forward": False
        }

    ls = kpts[LEFT_SHOULDER]
    rs = kpts[RIGHT_SHOULDER]
    lh = kpts[LEFT_HIP]
    rh = kpts[RIGHT_HIP]
    lw = kpts[LEFT_WRIST]
    rw = kpts[RIGHT_WRIST]

    shoulder_y = (ls[1] + rs[1]) / 2
    hip_y = (lh[1] + rh[1]) / 2
    wrist_y = (lw[1] + rw[1]) / 2

    # Heuristics (simple, fast, robust)
    crouching = (hip_y - shoulder_y) < 40   # compressed torso
    arms_raised = wrist_y < shoulder_y      # wrists above shoulders

    # Reaching forward ≈ wrists far from torso center (x-axis spread)
    torso_x = (ls[0] + rs[0]) / 2
    reach_dist = (abs(lw[0] - torso_x) + abs(rw[0] - torso_x)) / 2
    reaching_forward = reach_dist > 60

    return {
        "crouching": bool(crouching),
        "arms_raised": bool(arms_raised),
        "reaching_forward": bool(reaching_forward)
    }