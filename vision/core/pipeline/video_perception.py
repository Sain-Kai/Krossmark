from vision.core.pipeline.video_utils import sample_keyframes
from vision.core.vlm.video_prompts import VIDEO_ANALYSIS_PROMPT
from vision.core.vlm.parser import parse_vlm_json
from vision.core.audio.worker import HTSATWorker
from vision.core.vlm.ollama_vl import OllamaVLM
from vision.core.fusion.sensor_fusion import build_sensor_context


class VideoPerceptionPipeline:

    def __init__(self, htsat_model, vlm_model):
        self.htsat = HTSATWorker(htsat_model)
        self.vlm = OllamaVLM(model_name=vlm_model)

    def analyze_burst(self, frames, audio_3s, sensor_data=None):

        sensor_context = build_sensor_context(sensor_data)

        # 1️⃣ Sample keyframes
        keyframes = sample_keyframes(frames, k=6)

        # 2️⃣ Audio processing
        self.htsat.submit(audio_3s)
        audio_features = self.htsat.poll()

        # 3️⃣ Video reasoning
        text = self.vlm.infer_video(keyframes, VIDEO_ANALYSIS_PROMPT)
        parsed = parse_vlm_json(text)

        if parsed is None:
            return {
                "decision": "REQUEST_MORE_DATA",
                "confidence": 0.3,
                "sensor_context": sensor_context,
            }

        # 4️⃣ Fuse audio boost
        metallic = max([a.get("metallic", 0) for a in audio_features], default=0)
        shout = max([a.get("shout", 0) for a in audio_features], default=0)

        if metallic > 0.6 or shout > 0.6:
            parsed["threat_level"] = min(5, parsed.get("threat_level", 3) + 1)
            parsed["confidence"] = min(1.0, parsed.get("confidence", 0.6) + 0.1)

        # 5️⃣ Sensor boost
        sensor_score = sensor_context.get("sensor_score", 0.0)
        if sensor_context.get("sensor_alert"):
            parsed["threat_level"] = min(5, parsed.get("threat_level", 3) + 1)
            parsed["confidence"] = min(1.0, parsed.get("confidence", 0.6) + 0.08 + 0.12 * sensor_score)
        elif sensor_score > 0.35:
            parsed["confidence"] = min(1.0, parsed.get("confidence", 0.6) + 0.05 * sensor_score)

        parsed["sensor_context"] = sensor_context

        return parsed
