import math

def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])

def pose_features(kp):
    if kp is None:
        return {}

    lw, rw = kp["left_wrist"], kp["right_wrist"]
    ls, rs = kp["left_shoulder"], kp["right_shoulder"]
    le, re = kp["left_elbow"], kp["right_elbow"]

    feats = {}

    # Arms raised?
    feats["left_arm_raised"] = lw[1] < ls[1]
    feats["right_arm_raised"] = rw[1] < rs[1]

    # Arm extended forward (approx via elbow-wrist distance)
    feats["left_arm_extended"] = dist(lw, le) > 0.8 * dist(le, ls)
    feats["right_arm_extended"] = dist(rw, re) > 0.8 * dist(re, rs)

    # Aggressive posture heuristic
    feats["aggressive_pose"] = (
        (feats["left_arm_raised"] or feats["right_arm_raised"]) and
        (feats["left_arm_extended"] or feats["right_arm_extended"])
    )

    return feats