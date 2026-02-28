import cv2
from vision.core.detection.yolo import YoloDetector
from vision.core.evidence.accumulator import EvidenceAccumulator
from vision.core.features.grouping import group_tracks
from vision.core.features.motion import compute_speed, compute_direction
from vision.core.intent.group import GroupIntentEngine
from vision.core.intent.per_person import PersonIntentEngine
from vision.core.intent.scene import SceneIntentEngine
from vision.core.threat.scorer import ThreatScorer
from vision.core.tracking.tracker import SimpleTracker
from vision.core.vlm.ollama_vl import OllamaVLM
from vision.core.vlm.parser import parse_vlm_json
from vision.core.vlm.prompts import HAND_CROP_PROMPT, FULL_FRAME_PROMPT
from vision.core.vlm.scheduler import VLMScheduler
from vision.core.vlm.worker import VLMWorker

# Stage 5 Imports
from vision.core.fusion.stabilizer import SceneStabilizer
from vision.core.fusion.explainer import Explainer
from vision.core.fusion.packer import OutputPacker


class PerceptionPipeline:
    def __init__(self, yolo_path, qwen_dir, cfg):
        self.detector = YoloDetector(yolo_path, conf=cfg["CONF"], iou=cfg["IOU"])
        self.tracker = SimpleTracker()
        self.scheduler = VLMScheduler(cfg["VLM_COOLDOWN"])
        self.evidence = EvidenceAccumulator(cfg["EVIDENCE_WINDOW"], cfg["CONFIRM_THRESHOLD"])
        self.frame_idx = 0

        # VLM Threading Components
        self.vlm = OllamaVLM(model_name=cfg["QWEN_MODEL"])
        self.vlm_worker = VLMWorker(self.vlm)

        # Intelligence Engines
        self.person_intent_engine = PersonIntentEngine()
        self.group_intent_engine = GroupIntentEngine()
        self.scene_intent_engine = SceneIntentEngine()
        self.threat_scorer = ThreatScorer()

        # Global Signal Storage
        self.global_weapon_hint = None

        # Stage 5 Logic
        self.stabilizer = SceneStabilizer(window=10, hysteresis=3)
        self.explainer = Explainer()
        self.packer = OutputPacker()

    def threat_from_features(self, speed, groups_count):
        threat = 1
        if speed > 50: threat = 2
        if groups_count > 1: threat = max(threat, 3)
        return threat

    def crop_hands(self, frame, bbox):
        """Specialized crop focusing on upper body/hands area for weapon detection."""
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = map(int, bbox)
        # Tighten crop to top 2/3 of the person to focus on hands/waist
        y2 = y1 + int((y2 - y1) * 0.7)
        x1, x2 = max(0, min(x1, w - 1)), max(0, min(x2, w))
        y1, y2 = max(0, min(y1, h - 1)), max(0, min(y2, h))
        if x2 <= x1 or y2 <= y1: return None
        return frame[y1:y2, x1:x2]

    def process(self, frame):
        self.frame_idx += 1

        # 1. Collect and Fuse VLM Results (Dual Signal)
        vlm_results = self.vlm_worker.poll_results()
        for track_id, kind, text in vlm_results:
            parsed = parse_vlm_json(text)
            if not parsed: continue

            if kind == "hand" and track_id >= 0:
                # Per-track evidence (Precision)
                self.evidence.update(track_id, parsed)
            elif kind == "full":
                # Global frame context (Recall)
                self.global_weapon_hint = parsed

        # 2. Submit Global Context Job (Every 60 frames)
        if self.frame_idx % 60 == 0:
            self.vlm_worker.submit(-1, frame.copy(), FULL_FRAME_PROMPT, kind="full")

        # 3. Detection and Tracking
        detections = self.detector.detect(frame)

        # COCO class 0 = person
        person_dets = [d for d in detections if d["cls"] == 0]

        tracks = self.tracker.update(person_dets)
        groups = group_tracks(tracks)

        actors = []
        person_intents = []
        weapon_states = []

        for t in tracks:
            speed = compute_speed(t)
            direction = compute_direction(t)
            threat_hint = self.threat_from_features(speed, len(groups))

            # 4. Submit Hand Crop Job (When scheduler allows)
            if self.scheduler.should_call(t.id, self.frame_idx, threat_hint, True):
                crop = self.crop_hands(frame, t.bbox)
                if crop is not None:
                    self.vlm_worker.submit(t.id, crop, HAND_CROP_PROMPT, kind="hand")

            # Get current state from Evidence Accumulator
            current_weapon_state = self.evidence.get_state(t.id)
            intent = self.person_intent_engine.update(t.id, {"speed": speed, "direction": direction},
                                                      current_weapon_state)

            actors.append({
                "id": t.id,
                "bbox": t.bbox,
                "speed": speed,
                "direction": direction,
                "intent": intent,
                "weapon_state": current_weapon_state
            })

            person_intents.append(intent)
            weapon_states.append(current_weapon_state)

        # 5. Global Reasoning (Passing the Global Hint for Fusion)
        group_intent = self.group_intent_engine.update(groups)
        scene_intent = self.scene_intent_engine.update(person_intents, group_intent)

        # Scorer now fuses per-person weapon_states with the global_weapon_hint
        threat_level = self.threat_scorer.score(
            person_intents,
            group_intent,
            weapon_states,
            self.global_weapon_hint
        )

        # 6. Stabilization and Output Packing
        stable_scene, stable_threat = self.stabilizer.update(scene_intent, threat_level)
        explanations = self.explainer.explain(actors, group_intent, stable_scene, stable_threat)

        final_output = self.packer.pack(
            actors=actors,
            group_intent=group_intent,
            scene_intent=stable_scene,
            threat_level=stable_threat,
            explanations=explanations
        )

        return final_output, tracks