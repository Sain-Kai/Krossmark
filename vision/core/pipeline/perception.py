# vision/core/pipeline/perception.py

import numpy as np
from vision.core.detection.yolo import YoloDetector
from vision.core.tracking.deepsort_tracker import DeepSortTracker
from vision.core.detection.yolo_pose import YoloPose
from vision.core.features.pose_features import posture_from_keypoints_dict
from vision.core.vlm.ollama_vl import OllamaVLM
from vision.core.vlm.parser import parse_vlm_json
from vision.core.vlm.prompts import FULL_FRAME_PROMPT
from vision.core.audio.worker import HTSATWorker
from vision.core.threat.threat_engine import ThreatEngine
from vision.core.fusion.sensor_fusion import build_sensor_context


class PerceptionPipeline:

    def __init__(self, yolo_path, pose_path, htsat_model, cfg):

        self.detector = YoloDetector(
            yolo_path,
            conf=cfg["CONF"],
            iou=cfg["IOU"],
            imgsz=cfg.get("YOLO_IMGSZ", 960)
        )

        self.tracker = DeepSortTracker()

        self.pose = YoloPose(pose_path)

        self.vlm = OllamaVLM(model_name=cfg["QWEN_MODEL"])

        self.htsat = HTSATWorker(htsat_model)

        self.threat_engine = ThreatEngine()

    # ==========================================================
    # 3 SECOND BURST ANALYSIS
    # ==========================================================
    def analyze_burst(self, frames, audio_3s, sensor_data=None):

        fused_frames = []
        sensor_context = build_sensor_context(sensor_data)

        # submit audio once
        self.htsat.submit(audio_3s)
        audio_features = self.htsat.poll()

        for frame in frames:

            detections = self.detector.detect(frame)

            person_dets = [d for d in detections if d["cls"] == 0]

            tracks = self.tracker.update(person_dets, frame)

            person_boxes = [t["bbox"] for t in tracks]

            # ---------- POSE ----------
            poses = self.pose.infer(frame, person_boxes)

            pose_flags = []
            for kp in poses:
                feats = posture_from_keypoints_dict(kp)
                pose_flags.append(feats)

            # a---------- VLM (FULL FRAME ALWAYS) ----------
            text = self.vlm.infer(frame, FULL_FRAME_PROMPT)
            parsed = parse_vlm_json(text)

            fused_frames.append({
                "pose_feats": pose_flags,
                "vlm": parsed
            })

        audio_events = self.htsat.poll()

        fused = {
            "frames": fused_frames,
            "audio": audio_events,
            "sensor": sensor_context,
        }

        result = self.threat_engine.compute(fused, sensor_data=sensor_context)

        return result
