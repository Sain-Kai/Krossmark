from vision.core.features.pose_features import posture_from_keypoints_dict
from vision.core.vlm.parser import parse_vlm_json
from vision.core.vlm.prompts import HAND_CROP_PROMPT
from vision.core.fusion.sensor_fusion import build_sensor_context


class VideoBurstAnalyzer:

    def __init__(self, detector, tracker, pose, htsat, vlm, evidence):
        self.detector = detector
        self.tracker = tracker
        self.pose = pose
        self.htsat = htsat
        self.vlm = vlm
        self.evidence = evidence

    def analyze(self, frames, audio_3s, sensor_data=None):

        sensor_context = build_sensor_context(sensor_data)
        temporal_tracks = {}
        frame_features = []

        # 1️⃣ Audio first
        self.htsat.submit(audio_3s)
        audio_features = self.htsat.poll()

        # 2️⃣ Frame loop
        for frame_idx, frame in enumerate(frames):

            detections = self.detector.detect(frame)
            person_dets = [d for d in detections if d["cls"] == 0]

            tracks = self.tracker.update(person_dets, frame)

            for t in tracks:
                tid = t["id"]

                if tid not in temporal_tracks:
                    temporal_tracks[tid] = {
                        "history": [],
                        "pose_flags": []
                    }

                # Motion history
                x1, y1, x2, y2 = t["bbox"]
                cx = (x1 + x2) / 2
                cy = (y1 + y2) / 2

                temporal_tracks[tid]["history"].append(
                    (cx, cy, frame_idx)
                )

                # Pose
                kpts = self.pose.infer(frame, [t["bbox"]])[0]
                feats = posture_from_keypoints_dict(kpts)

                temporal_tracks[tid]["pose_flags"].append(feats)

                # Weapon crop VLM (precision layer)
                if feats.get("reaching_forward"):
                    text = self.vlm.infer(frame, HAND_CROP_PROMPT)
                    parsed = parse_vlm_json(text)
                    if parsed:
                        self.evidence.update(tid, parsed)

        return {
            "tracks": temporal_tracks,
            "audio": audio_features,
            "frames": frames,
            "sensor": sensor_context,
        }
