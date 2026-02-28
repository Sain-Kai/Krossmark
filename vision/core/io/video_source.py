import cv2

class VideoSource:
    def __init__(self, src):
        self.cap = cv2.VideoCapture(src)
        if not self.cap.isOpened():
            raise RuntimeError("Cannot open video source")

    def read(self):
        return self.cap.read()

    def release(self):
        self.cap.release()