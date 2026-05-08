from __future__ import annotations
from typing import Any, Dict, Optional
import traceback
import numpy as np

from django.conf import settings
from .media import load_frames_from_video, load_audio_from_wav


def _safe_fallback_result(meta: Dict[str, Any]) -> Dict[str, Any]:
    threat = 3 if meta.get("mic_triggered") else 1
    confidence = 0.48 if threat == 3 else 0.4
    return {
        "threat_level": threat,
        "confidence": confidence,
        "group_intent": "GroupIntent.LOOSE" if meta.get("people_hint", 1) > 1 else "GroupIntent.NONE",
        "scene_intent": "SceneIntent.SUSPICIOUS" if threat >= 3 else "SceneIntent.NORMAL",
        "briefing": "Fallback analysis used because the full vision stack was not available.",
        "audit": {
            "fallback": True,
            "mic_triggered": bool(meta.get("mic_triggered")),
            "source": meta.get("source", "backend"),
            "sensor_context": meta.get("sensor_context", {}),
        },
        "actors": meta.get("actors", []),
        "video_context": {
            "weapon_present": False,
            "weapon_type": "none",
            "people_count": meta.get("people_hint", 1),
            "coordinated_activity": False,
            "aggressive_behavior": False,
            "confidence": confidence,
        },
        "decision": "REQUEST_MORE_DATA" if threat < 3 else "CONFIRM_THREAT",
        "raw_output": {"mode": "fallback", "sensor_context": meta.get("sensor_context", {})},
    }


class DefenseAnalysisService:
    """
    Adapter around your existing Python pipeline.
    Falls back safely if the pipeline package is not importable in the Django runtime.
    """

    def __init__(self):
        self._pipeline = None
        self._pipeline_ready = False
        self._init_error = None

    def _ensure_pipeline(self):
        if self._pipeline_ready:
            return self._pipeline

        try:
            from vision.core.pipeline.defense_ai_pipeline import DefenseAIPipeline
            from vision.core.detection.yolo import YoloDetector
            from vision.core.tracking.deepsort_tracker import DeepSortTracker
            from vision.core.pose.rtm_pose import RTMPoseEstimator
            from vision.core.vlm.ollama_vl import OllamaVLM
            from vision.core.audio.worker import HTSATWorker
            from vision.core.config import YOLO_DET_MODEL, HTSAT_MODEL, QWEN_MODEL_NAME, CONF_THRESH, IOU_THRESH, YOLO_IMGSZ
        except Exception as exc:
            self._init_error = exc
            self._pipeline_ready = True
            self._pipeline = None
            return None

        try:
            class DefaultPoseModel:
                def infer(self, crop):
                    h, w = crop.shape[:2]
                    return {
                        "left_wrist": (w * 0.3, h * 0.45),
                        "right_wrist": (w * 0.7, h * 0.45),
                        "left_elbow": (w * 0.3, h * 0.55),
                        "right_elbow": (w * 0.7, h * 0.55),
                        "left_shoulder": (w * 0.3, h * 0.65),
                        "right_shoulder": (w * 0.7, h * 0.65),
                    }

            detector = YoloDetector(YOLO_DET_MODEL, conf=CONF_THRESH, iou=IOU_THRESH, imgsz=YOLO_IMGSZ)
            tracker = DeepSortTracker()
            pose = RTMPoseEstimator(DefaultPoseModel())
            vlm = OllamaVLM(model_name=QWEN_MODEL_NAME, url=getattr(settings, "OLLAMA_URL", "http://localhost:11434/api/generate"))
            htsat = HTSATWorker(HTSAT_MODEL)

            self._pipeline = DefenseAIPipeline(
                detector=detector,
                tracker=tracker,
                pose_estimator=pose,
                vlm=vlm,
                htsat=htsat,
            )
            self._pipeline_ready = True
            return self._pipeline
        except Exception as exc:
            self._init_error = exc
            self._pipeline_ready = True
            self._pipeline = None
            return None

    def analyze_burst(self, burst):
        pipeline = self._ensure_pipeline()

        meta = dict(burst.metadata or {})
        meta.update({
            "mic_triggered": bool(getattr(burst.trigger, "mic_triggered", False)),
            "source": "django",
            "people_hint": int(meta.get("people_hint", 1) or 1),
        })

        sensor_payload = {}
        trigger_sensor = getattr(burst.trigger, "sensor_payload", None)
        if isinstance(trigger_sensor, dict):
            sensor_payload = trigger_sensor
        elif isinstance(meta.get("sensor_data"), dict):
            sensor_payload = meta.get("sensor_data", {})
        elif isinstance(meta.get("sensor_payload"), dict):
            sensor_payload = meta.get("sensor_payload", {})

        meta["sensor_context"] = sensor_payload

        if pipeline is None:
            result = _safe_fallback_result(meta)
            if self._init_error:
                result["audit"]["pipeline_error"] = str(self._init_error)
            return result

        try:
            frames = []
            if burst.video_file:
                frames = load_frames_from_video(burst.video_file.path, max_frames=6)

            audio = None
            if burst.audio_file:
                audio = load_audio_from_wav(burst.audio_file.path)

            if not frames:
                return _safe_fallback_result(meta)

            return pipeline.analyze_burst(frames, audio, sensor_data=sensor_payload)
        except Exception as exc:
            fallback = _safe_fallback_result(meta)
            fallback["audit"]["analysis_error"] = str(exc)
            fallback["audit"]["traceback"] = traceback.format_exc(limit=3)
            return fallback


def result_to_alert_severity(threat_level: int) -> str:
    if threat_level >= 5:
        return "critical"
    if threat_level == 4:
        return "high"
    if threat_level == 3:
        return "medium"
    if threat_level == 2:
        return "low"
    return "info"
