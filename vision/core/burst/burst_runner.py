# vision/core/burst/burst_runner.py

import cv2
import time
import numpy as np

from vision.core.audio.worker import HTSATWorker
from vision.core.pipeline.perception import PerceptionPipeline
from vision.core.config import *

CFG = {
    "CONF": CONF_THRESH,
    "IOU": IOU_THRESH,
    "YOLO_IMGSZ": 960,
    "QWEN_MODEL": QWEN_MODEL_NAME
}

YOLO_PATH = r"E:\Krossmark\models\yolo26\yolo26m.pt"
POSE_PATH = r"E:\Krossmark\models\yolo26\yolo26s-pose.pt"

#IMPORTANT: this must be your ACTUAL htsat model file
HTSAT_MODEL_PATH = r"E:\Krossmark\models\htsat"

# Initialize HTSAT properly
htsat_model = HTSATWorker(HTSAT_MODEL_PATH)

pipeline = PerceptionPipeline(
    YOLO_PATH,
    POSE_PATH,
    htsat_model,
    CFG
)

cap = cv2.VideoCapture(0)

frames = []
start = time.time()

print("[INFO] Capturing 3-second burst...")

while time.time() - start < 3:
    ret, frame = cap.read()
    if not ret:
        break
    frames.append(frame)

cap.release()

audio_3s = np.zeros((48000 * 3,))  # Replace with real mic capture

result = pipeline.analyze_burst(frames, audio_3s)

print("===== FINAL DECISION =====")
print(result)