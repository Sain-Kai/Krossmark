import argparse
import json
import os
import sys
from pathlib import Path

print("TEST.PY STARTED")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

BACKEND_DIR = PROJECT_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

print("PYTHONPATH:", sys.path)

import cv2
import sounddevice as sd
import time
import config

from vision.core.pipeline.defence_ai_pipeline import DefenseAIPipeline
from vision.core.detection.yolo import YoloDetector
from vision.core.tracking.deepsort_tracker import DeepSortTracker
from vision.core.pose.rtm_pose import RTMPoseEstimator
from vision.core.vlm.ollama_vl import OllamaVLM
from vision.core.audio.worker import HTSATWorker


def _load_trigger_payload() -> dict:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--trigger-payload-file", default=os.getenv("KROSSMARK_TRIGGER_PAYLOAD_FILE", ""))
    args, _ = parser.parse_known_args()

    payload = {}

    if args.trigger_payload_file:
        try:
            payload_path = Path(args.trigger_payload_file)
            if payload_path.exists():
                payload = json.loads(payload_path.read_text(encoding="utf-8"))
        except Exception as exc:
            print("[WARN] Failed to load trigger payload file:", exc)

    if not payload:
        raw_env = os.environ.get("KROSSMARK_TRIGGER_PAYLOAD", "{}")
        try:
            payload = json.loads(raw_env)
        except Exception as exc:
            print("[WARN] Failed to parse KROSSMARK_TRIGGER_PAYLOAD:", exc)
            payload = {}

    return payload if isinstance(payload, dict) else {}


trigger_payload = _load_trigger_payload()

sensor_data = trigger_payload.get("sensor_data") if isinstance(trigger_payload.get("sensor_data"), dict) else {}
if not sensor_data:
    sensor_data = {
        "adxl": trigger_payload.get("adxl") if isinstance(trigger_payload.get("adxl"), dict) else {},
        "fsr": trigger_payload.get("fsr") if isinstance(trigger_payload.get("fsr"), dict) else {},
    }

adxl_data = sensor_data.get("adxl") or {}
fsr_data = sensor_data.get("fsr") or {}
trigger_id = trigger_payload.get("trigger_id")
burst_id = trigger_payload.get("burst_id")

print("\n[SENSOR DATA FROM TRIGGER]")
print(
    f"  ADXL  : x={adxl_data.get('x', 'N/A')}  y={adxl_data.get('y', 'N/A')}  "
    f"z={adxl_data.get('z', 'N/A')}  mag={adxl_data.get('magnitude', 'N/A')}"
)
print(
    f"  FSR   : raw={fsr_data.get('raw', 'N/A')}  "
    f"resistance={fsr_data.get('resistance', 'N/A')} ohm  "
    f"force={fsr_data.get('force_g', 'N/A')} g"
)
print(f"  burst_id  : {burst_id}")
print(f"  trigger_id: {trigger_id}")

print("[INFO] Loading models...")

detector = YoloDetector(
    config.YOLO_DET_MODEL,
    conf=config.CONF_THRESH,
    iou=config.IOU_THRESH,
    imgsz=config.YOLO_IMGSZ
)

tracker = DeepSortTracker()


class DummyRTMModel:
    def infer(self, crop):
        h, w, _ = crop.shape
        return {
            "left_wrist": (w * 0.3, h * 0.4),
            "right_wrist": (w * 0.7, h * 0.4),
            "left_elbow": (w * 0.3, h * 0.5),
            "right_elbow": (w * 0.7, h * 0.5),
            "left_shoulder": (w * 0.3, h * 0.6),
            "right_shoulder": (w * 0.7, h * 0.6),
        }


pose_estimator = RTMPoseEstimator(DummyRTMModel())
htsat = HTSATWorker(config.HTSAT_MODEL)
vlm = OllamaVLM(model_name=config.QWEN_MODEL_NAME)

pipeline = DefenseAIPipeline(
    detector=detector,
    tracker=tracker,
    pose_estimator=pose_estimator,
    vlm=vlm,
    htsat=htsat,
)

print("[INFO] Models loaded successfully.")

print("[INFO] Processing Camera...")
cap = cv2.VideoCapture(config.VIDEO_SOURCE)
if not cap.isOpened():
    raise RuntimeError("Cannot open webcam")

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

actual_w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
actual_h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
print(f"[INFO] Cam resolution: {actual_w} x {actual_h}")

frames = []
start_time = time.time()

audio_buffer = sd.rec(
    int(config.BURST_SECONDS * config.AUDIO_SAMPLE_RATE),
    samplerate=config.AUDIO_SAMPLE_RATE,
    channels=1,
    dtype="float32",
)

while time.time() - start_time < config.BURST_SECONDS:
    ret, frame = cap.read()
    if not ret:
        break
    frames.append(frame)

sd.wait()
cap.release()
audio = audio_buffer.flatten()

print(f"[INFO] Captured {len(frames)} frames.")
print("[INFO] Audio captured.")

print("[INFO] Running Krossmark AI...")
try:
    result = pipeline.analyze_burst(frames, audio, sensor_data=sensor_data)
except TypeError:
    result = pipeline.analyze_burst(frames, audio)
    if isinstance(result, dict):
        result["sensor_data"] = sensor_data

print("\n==============================")
print("       DEFENSE AI RESULT")
print("==============================")

print(f"Threat Level : {result.get('threat_level', 'N/A')}")
print(f"Confidence   : {result.get('confidence', 0.0) * 100:.1f}%")
print(f"Group Intent : {result.get('group_intent', 'N/A')}")

if "scene_intent" in result:
    print(f"Scene Intent : {result['scene_intent']}")
else:
    print("Scene Intent : Not Calculated")

print("\n--- ANALYST BRIEFING ---")
print(result.get("briefing", "No briefing generated."))

audio_result = result.get("audio_result") or result.get("video_context", {}).get("audio", {}) or {}

print("\n--- AUDIO READINGS ---")
if audio_result:
    print(
        f" Dominant Sound : {audio_result.get('dominant_sound_type', 'unknown')} "
        f"({float(audio_result.get('dominant_sound_confidence', 0.0)) * 100:.1f}%)"
    )
    print(f" Audio Threat    : {float(audio_result.get('threat_score', 0.0)):.3f}")
    print(f" Description     : {audio_result.get('audio_description', audio_result.get('summary', 'N/A'))}")

    print("\n Top Sound Labels:")
    sound_scores = audio_result.get("sound_type_scores", {})
    if isinstance(sound_scores, dict) and sound_scores:
        for k, v in sorted(sound_scores.items(), key=lambda kv: kv[1], reverse=True)[:8]:
            print(f" - {k}: {float(v):.3f}")

    events = audio_result.get("audio_events", [])
    if events:
        print("\n Audio Events:")
        for ev in events[:8]:
            if isinstance(ev, dict):
                print(f" - {ev.get('sound_type', 'unknown')}: {float(ev.get('confidence', 0.0)):.3f}")
else:
    print(" No audio result returned.")

print("\nAudit Trail (Bayesian Inputs):")
for key, value in result.get("audit", {}).items():
    print(f" - {key}: {value}")

print("\n--- SENSOR READINGS ---")
print(
    f" ADXL x={adxl_data.get('x', 'N/A')}  y={adxl_data.get('y', 'N/A')}  "
    f"z={adxl_data.get('z', 'N/A')}  magnitude={adxl_data.get('magnitude', 'N/A')}"
)
print(
    f" FSR  raw={fsr_data.get('raw', 'N/A')}  "
    f"resistance={fsr_data.get('resistance', 'N/A')} ohm  "
    f"force={fsr_data.get('force_g', 'N/A')} g"
)

print("\nActors Detected:")
if not result.get("actors"):
    print(" No persistent actors tracked in this burst.")
for actor in result.get("actors", []):
    print(f" - {actor}")

print("\n[INFO] Live test completed.")

print("\n[DB] Saving result to database...")

try:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "krossmark_backend.settings")

    import django
    django.setup()

    from surveillance.models import Device, TriggerEvent, BurstCapture, AnalysisResult

    device, created = Device.objects.get_or_create(
        serial_number="PI-RELAY-001",
        defaults={
            "name": "Raspberry Pi Relay",
            "device_type": getattr(Device.DeviceType, "PI", "pi"),
            "location_tag": "entrance",
        },
    )
    if created:
        print(f"[DB] Created new device. API key: {device.api_key}")

    trigger_obj = None
    if trigger_id:
        try:
            trigger_obj = TriggerEvent.objects.get(id=trigger_id)
            print(f"[DB] Linked to existing TriggerEvent {trigger_id}")
        except TriggerEvent.DoesNotExist:
            print(f"[DB] TriggerEvent {trigger_id} not found — will create new one")

    if trigger_obj is None:
        trigger_obj = TriggerEvent.objects.create(
            device=device,
            source_level=getattr(TriggerEvent.SourceLevel, "PI", "pi"),
            pir_triggered=False,
            mic_triggered=False,
            confidence=0.0,
            sensor_payload={
                "adxl": adxl_data,
                "fsr": fsr_data,
            },
        )
        print(f"[DB] Created TriggerEvent {trigger_obj.id}")

    burst = BurstCapture.objects.create(
        device=device,
        trigger=trigger_obj,
        frame_count=len(frames),
        audio_sample_rate=int(getattr(config, "AUDIO_SAMPLE_RATE", 48000)),
        metadata={
            "people_hint": len(result.get("actors", [])) or 1,
            "adxl": adxl_data,
            "fsr": fsr_data,
            "burst_id_from_pi": burst_id,
            "sensor_data": sensor_data,
        },
    )

    AnalysisResult.objects.create(
        burst=burst,
        threat_level=int(result.get("threat_level", 1) or 1),
        confidence=float(result.get("confidence", 0.0) or 0.0),
        group_intent=str(result.get("group_intent", "")),
        scene_intent=str(result.get("scene_intent", "Not Calculated")),
        decision=str(result.get("decision", "")),
        briefing=str(result.get("briefing", "")),
        audit=result.get("audit", {}),
        actors=result.get("actors", []),
        video_context=result.get("video_context", {}),
        raw_output={
            **result,
            "sensor_data": sensor_data,
            "audio_result": audio_result,
        },
    )

    print("[DB] Result saved successfully — app will update on next poll.")

except Exception as e:
    print(f"[DB] Failed to save to database: {e}")
    import traceback
    traceback.print_exc()