import numpy as np

# COCO keypoints indices (YOLO format usually follows COCO)
NOSE = 0
LEFT_SHOULDER = 5
RIGHT_SHOULDER = 6
LEFT_HIP = 11
RIGHT_HIP = 12
LEFT_WRIST = 9
RIGHT_WRIST = 10

def posture_from_keypoints_dict(kpts):

    if not kpts:
        return {
            "crouching": False,
            "arms_raised": False,
            "reaching_forward": False
        }

    ls = kpts["left_shoulder"]
    rs = kpts["right_shoulder"]
    lw = kpts["left_wrist"]
    rw = kpts["right_wrist"]

    shoulder_y = (ls[1] + rs[1]) / 2
    wrist_y = (lw[1] + rw[1]) / 2

    crouching = False
    arms_raised = wrist_y < shoulder_y

    torso_x = (ls[0] + rs[0]) / 2
    reach_dist = (abs(lw[0] - torso_x) + abs(rw[0] - torso_x)) / 2
    reaching_forward = reach_dist > 60

    return {
        "crouching": crouching,
        "arms_raised": arms_raised,
        "reaching_forward": reaching_forward
    }