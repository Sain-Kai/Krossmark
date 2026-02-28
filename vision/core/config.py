# Paths (adjust to your system)
YOLO_DET_MODEL = r"E:\Krossmark\models\yolo26\yolo26m.pt"
QWEN_VL_DIR = r"E:\Krossmark\models\qwen-vl-4b-quant"  # local HF folder or model id
QWEN_MODEL_NAME = "qwen3-vl:4b"  # or whatever `ollama list` shows
VIDEO_SOURCE = 0  # webcam or path
VLM_COOLDOWN_FRAMES = 120  # ~4 seconds at 30 FPS
CONF_THRESH = 0.3
IOU_THRESH = 0.5
YOLO_IMGSZ = 960
# VLM scheduling
VLM_COOLDOWN_FRAMES = 30
THREAT_LOW = 1
THREAT_HIGH = 4

# Evidence
EVIDENCE_WINDOW = 10
CONFIRM_THRESHOLD = 0.6