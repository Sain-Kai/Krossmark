import requests
import base64
import cv2


class OllamaVLM:

    def __init__(self, model_name="qwen3-vl:4b", url="http://localhost:11434/api/generate"):
        self.model = model_name
        self.url = url

    def _encode_image(self, img_bgr):

        # 🔥 Downscale to reduce vision tokens
        h, w = img_bgr.shape[:2]

        max_side = 640  # critical
        scale = max_side / max(h, w)

        if scale < 1:
            img_bgr = cv2.resize(img_bgr, None, fx=scale, fy=scale)

        _, buf = cv2.imencode(".jpg", img_bgr,
                              [int(cv2.IMWRITE_JPEG_QUALITY), 90])

        return base64.b64encode(buf.tobytes()).decode("utf-8")

    # ===============================
    # MULTI-FRAME (VIDEO)
    # ===============================
    def infer_video(self, frames, prompt, timeout=600):

        if frames is None or len(frames) == 0:
            return ""

        images_b64 = [self._encode_image(f) for f in frames]

        payload = {
            "model": self.model,
            "prompt": prompt,
            "images": images_b64,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.0,
                "num_predict": 256
            }
        }

        try:
            r = requests.post(self.url, json=payload, timeout=timeout)
            r.raise_for_status()

            data = r.json()

            print("\n[VLM FULL RESPONSE JSON]")
            print(data)

            response = data.get("response", "")

            if not response:
                response = data.get("thinking", "")

            return response

        except Exception as e:
            print("[VLM Video Error]:", e)
            return ""
    # ===============================
    # SINGLE IMAGE (OPTIONAL)
    # ===============================
    def infer_image(self, image, prompt, timeout=600):

        if image is None:
            print("[VLM] No image provided.")
            return ""

        img_b64 = self._encode_image(image)

        payload = {
            "model": self.model,
            "prompt": prompt,
            "images": [img_b64],
            "stream": False,
            "options": {
                "temperature": 0.0,
                "num_predict": 256
            }
        }

        try:
            r = requests.post(self.url, json=payload, timeout=timeout)
            r.raise_for_status()
            data = r.json()

            response = data.get("response", "")

            print("\n[VLM RAW IMAGE OUTPUT]")
            print(response)

            return response

        except Exception as e:
            print("[VLM Image Error]:", e)
            return ""