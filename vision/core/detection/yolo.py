from ultralytics import YOLO

class YoloDetector:
    def __init__(self, model_path, conf=0.15, iou=0.45, imgsz=960):
        self.model = YOLO(model_path)
        self.conf = conf
        self.iou = iou
        self.imgsz = imgsz

    def detect(self, frame):
        results = self.model.predict(
            frame,
            conf=self.conf,
            iou=self.iou,
            imgsz=self.imgsz,
            verbose=False
        )

        detections = []

        for r in results:
            if r.boxes is None:
                continue

            for box in r.boxes:
                cls = int(box.cls[0])
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])

                detections.append({
                    "cls": cls,
                    "conf": conf,
                    "bbox": (x1, y1, x2, y2)
                })

        return detections