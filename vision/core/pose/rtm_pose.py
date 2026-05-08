import numpy as np


class RTMPoseEstimator:

    def __init__(self, model):
        self.model = model

    def estimate(self, frame, person_bbox):

        x1, y1, x2, y2 = map(int, person_bbox)

        # Clamp bbox to image boundaries
        h, w = frame.shape[:2]
        x1 = max(0, min(w - 1, x1))
        x2 = max(0, min(w - 1, x2))
        y1 = max(0, min(h - 1, y1))
        y2 = max(0, min(h - 1, y2))

        crop = frame[y1:y2, x1:x2]

        if crop is None or crop.size == 0:
            print("[RTMPose] Empty crop.")
            return None

        try:
            kpts = self.model.infer(crop)
        except Exception as e:
            print("[RTMPose] Model inference failed:", e)
            return None

        if not kpts:
            print("[RTMPose] No keypoints detected.")
            return None

        try:
            def map_pt(p):
                return (int(p[0] + x1), int(p[1] + y1))

            mapped = {
                "left_wrist": map_pt(kpts["left_wrist"]),
                "right_wrist": map_pt(kpts["right_wrist"]),
                "left_elbow": map_pt(kpts["left_elbow"]),
                "right_elbow": map_pt(kpts["right_elbow"]),
                "left_shoulder": map_pt(kpts["left_shoulder"]),
                "right_shoulder": map_pt(kpts["right_shoulder"]),
            }

            return mapped

        except Exception as e:
            print("[RTMPose] Keypoint mapping failed:", e)
            return None