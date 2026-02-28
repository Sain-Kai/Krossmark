import requests
import base64
import cv2
import time

class OllamaVLM:
    def __init__(self, model_name="qwen3-vl:4b", url="http://localhost:11434/api/generate"):
        self.model = model_name
        self.url = url

    def _encode_image(self, img_bgr):
        _, buf = cv2.imencode(".jpg", img_bgr)
        return base64.b64encode(buf.tobytes()).decode("utf-8")

    def infer(self, img_bgr, prompt, timeout=600, retries=2):
        img_b64 = self._encode_image(img_bgr)

        payload = {
            "model": self.model,
            "prompt": prompt,
            "images": [img_b64],
            "stream": False,
            "options": {
                "temperature": 0.0
            }
        }

        last_err = None
        for attempt in range(retries + 1):
            try:
                r = requests.post(self.url, json=payload, timeout=timeout)
                r.raise_for_status()
                data = r.json()
                return data.get("response", "")
            except Exception as e:
                print(f"[VLM] Attempt {attempt+1} failed: {e}")
                last_err = e
                time.sleep(2)

        print("[VLM] All attempts failed, skipping this frame.")
        return ""