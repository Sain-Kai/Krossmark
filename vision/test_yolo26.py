import cv2
from ultralytics import YOLO

MODEL_PATH = r"E:\Krossmark\models\yolo26\yolo26m.pt"
VIDEO_SOURCE = 0

model = YOLO(MODEL_PATH)
print("[INFO] Model loaded:", MODEL_PATH)

cap = cv2.VideoCapture(VIDEO_SOURCE)

while True:
    ret, frame = cap.read()
    if not ret:
        break

    results = model.predict(frame, conf=0.25, iou=0.45, imgsz=960, verbose=False)

    for r in results:
        if r.boxes is None:
            continue

        for box in r.boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = map(int, box.xyxy[0])

            name = model.names.get(cls, str(cls))

            # Draw EVERYTHING
            cv2.rectangle(frame, (x1,y1), (x2,y2), (0,255,0), 2)
            cv2.putText(frame, f"{name} {conf:.2f}", (x1, y1-5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 2)

            print(f"Detected: {name} {conf:.2f}")

    cv2.imshow("YOLO26 Full Output Test", frame)
    if cv2.waitKey(1) & 0xFF == 27:
        break

cap.release()
cv2.destroyAllWindows()