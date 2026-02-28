import numpy as np

class RTMPoseEstimator:
    def __init__(self, model):
        """
        model: your loaded RTMPose model (onnx/torch/mmpose wrapper)
        """
        self.model = model

    def estimate(self, frame, person_bbox):
        """
        Returns keypoints dict:
        {
          "left_wrist": (x,y), "right_wrist": (x,y),
          "left_elbow": (x,y), "right_elbow": (x,y),
          "left_shoulder": (x,y), "right_shoulder": (x,y)
        }
        Coordinates in image space.
        """
        x1, y1, x2, y2 = map(int, person_bbox)
        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return None

        # ---- Call your RTMPose here ----
        # This is pseudo; adapt to your API:
        kpts = self.model.infer(crop)  # returns Nx2 or dict

        # Map back to full-image coords
        def map_pt(p):
            return (int(p[0] + x1), int(p[1] + y1))

        keypoints = {
            "left_wrist": map_pt(kpts["left_wrist"]),
            "right_wrist": map_pt(kpts["right_wrist"]),
            "left_elbow": map_pt(kpts["left_elbow"]),
            "right_elbow": map_pt(kpts["right_elbow"]),
            "left_shoulder": map_pt(kpts["left_shoulder"]),
            "right_shoulder": map_pt(kpts["right_shoulder"]),
        }
        return keypoints