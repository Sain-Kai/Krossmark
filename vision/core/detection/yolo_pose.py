import numpy as np
from ultralytics import YOLO


class YoloPose:
    def __init__(self, model_path, conf=0.4):
        self.model = YOLO(model_path)
        self.conf = conf

    def infer(self, frame, person_bboxes):
        """
        Runs pose only on cropped persons and maps coordinates back to original frame.
        """
        poses = []

        for box in person_bboxes:
            x1, y1, x2, y2 = map(int, box)
            crop = frame[y1:y2, x1:x2]

            # 1. Check if crop is valid
            if crop.size == 0 or crop.shape[0] < 5 or crop.shape[1] < 5:
                poses.append(None)
                continue

            results = self.model.predict(crop, conf=self.conf, verbose=False)

            # 2. Safety check for empty detections in the crop
            if not results or results[0].keypoints is None or len(results[0].keypoints.data) == 0:
                poses.append(None)
                continue

            # 3. Extract keypoints (N, K, 2)
            # We use .data to get (N, K, 3) if you want confidence, or .xy for just coords
            kpts = results[0].keypoints.xy.cpu().numpy()

            if kpts.shape[0] > 0:
                person_kpts = kpts[0]  # Take the most confident person in the crop

                # 4. CRITICAL: Map coordinates back to the original full frame
                # Without this, your pose coordinates are relative to the (0,0) of the crop
                person_kpts[:, 0] += x1  # Add crop offset X
                person_kpts[:, 1] += y1  # Add crop offset Y

                poses.append(person_kpts)
            else:
                poses.append(None)

        return poses