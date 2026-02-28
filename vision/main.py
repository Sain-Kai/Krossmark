import cv2
import numpy as np
import ollama
import json
from core.io.video_source import VideoSource
from core.pipeline.perception import PerceptionPipeline
from core.config import (
    YOLO_DET_MODEL, VIDEO_SOURCE, CONF_THRESH, IOU_THRESH,
    VLM_COOLDOWN_FRAMES, EVIDENCE_WINDOW, CONFIRM_THRESHOLD, QWEN_MODEL_NAME
)

CFG = {
    "CONF": CONF_THRESH,
    "IOU": IOU_THRESH,
    "YOLO_IMGSZ": 960,
    "VLM_COOLDOWN": VLM_COOLDOWN_FRAMES,
    "EVIDENCE_WINDOW": EVIDENCE_WINDOW,
    "CONFIRM_THRESHOLD": CONFIRM_THRESHOLD,
    "QWEN_MODEL": QWEN_MODEL_NAME
}


def draw(frame, tracks, actors):
    """Draws boxes and per-actor intent labels."""
    for i, t in enumerate(tracks):
        x1, y1, x2, y2 = map(int, t.bbox)

        # Match track to actor safely
        a = next((item for item in actors if item["id"] == t.id), {})
        ws = a.get("weapon_state")
        intent = a.get("intent", "analyzing...")

        color = (0, 255, 0)  # Default: Green
        label = f"ID {t.id} | {intent}"

        if ws and isinstance(ws, dict):
            if ws.get("confirmed"):
                color = (0, 0, 255)  # Red
                label = f"!! ALERT: {ws.get('weapon')} !!"
            elif ws.get("weapon") not in ["none", "unknown", None]:
                color = (0, 165, 255)  # Orange
                label = f"? POSS {ws.get('weapon')} ?"

        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, label, (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)


if __name__ == "__main__":
    print(f"[INIT] Warming up {QWEN_MODEL_NAME}...")
    try:
        warmup_px = np.zeros((100, 100, 3), dtype=np.uint8)
        _, buf = cv2.imencode('.jpg', warmup_px)
        ollama.chat(model=QWEN_MODEL_NAME, messages=[{'role': 'user', 'content': 'ok', 'images': [buf.tobytes()]}])
        print("[INIT] Warmup successful.")
    except Exception as e:
        print(f"[CRITICAL] Connection Error: {e}")
        exit(1)

    vs = VideoSource(VIDEO_SOURCE)
    pipeline = PerceptionPipeline(YOLO_DET_MODEL, None, CFG)

    while True:
        ret, frame = vs.read()
        if not ret: break

        # Stage 5 logic returns final_output and tracks
        output, tracks = pipeline.process(frame)

        # 4. Render Actors
        draw(frame, tracks, output.get("actors", []))

        # --- Scene Intelligence Overlay ---
        # Draw stabilized scene intent and threat level
        cv2.putText(frame, f"Targets: {output['person_count']} Groups: {output['groups']}",
                    (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        cv2.putText(frame,
                    f"Scene: {output['scene_intent']} | Threat: {output['threat_level']} | Conf: {output.get('confidence', 1.0)}",
                    (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        # Print the detailed JSON packet to console for verification
        print(json.dumps(output, indent=2))

        cv2.imshow("Krossmark Live Security", frame)
        if cv2.waitKey(1) & 0xFF == 27: break

    vs.release()
    cv2.destroyAllWindows()