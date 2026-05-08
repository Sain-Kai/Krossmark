from __future__ import annotations

from typing import Any, Dict, Iterable, List

from vision.core.pipeline.video_utils import sample_keyframes
from vision.core.vlm.parser import parse_vlm_json
from vision.core.vlm.prompts import FULL_FRAME_PROMPT, VIDEO_ANALYSIS_PROMPT


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


class DefenseAIPipeline:
    """
    Vision + audio + sensor fusion pipeline.

    Fixes:
    - normal static scenes stay low
    - crowded active rooms get a meaningful vision score
    - weapon text in VLM output can escalate even when weapon_present is missing
    - silence forces audio threat to zero
    - final score no longer collapses crowded scenes into empty-scene scores
    """

    def __init__(self, detector, tracker, pose_estimator, vlm, htsat):
        self.detector = detector
        self.tracker = tracker
        self.pose_estimator = pose_estimator
        self.vlm = vlm
        self.htsat = htsat

    # ----------------------------------------------------------
    # Utilities
    # ----------------------------------------------------------
    def _normalize_sequence(self, value: Any) -> list:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, tuple):
            return list(value)
        return [value]

    def _safe_stringify_actor(self, actor: Any) -> dict:
        if isinstance(actor, dict):
            return actor

        out = {}
        for key in ("track_id", "id", "label", "class_name", "name", "score", "confidence"):
            if hasattr(actor, key):
                try:
                    out[key] = getattr(actor, key)
                except Exception:
                    pass

        for key in ("bbox", "tlwh", "xyxy"):
            if hasattr(actor, key):
                try:
                    value = getattr(actor, key)
                    if hasattr(value, "tolist"):
                        value = value.tolist()
                    out[key] = value
                except Exception:
                    pass

        if not out:
            out["repr"] = str(actor)
        return out

    def _pick_text(self, data: dict, keys: Iterable[str], default: str = "unknown") -> str:
        if not isinstance(data, dict):
            return default
        for key in keys:
            value = data.get(key)
            if value not in (None, "", []):
                return str(value)
        return default

    def _text_blob(self, vlm_result: Dict[str, Any]) -> str:
        parts = []
        for key in ("raw_text", "description", "summary", "briefing"):
            val = vlm_result.get(key)
            if isinstance(val, str) and val.strip():
                parts.append(val)
        return " ".join(parts).lower()

    def _weapon_hint_from_text(self, text: str) -> tuple[bool, str, float]:
        if not text:
            return False, "unknown", 0.0

        weapon_keywords = [
            ("gunfire", "firearm", 0.95),
            ("gunshot", "firearm", 0.95),
            ("firearm", "firearm", 0.95),
            ("handgun", "firearm", 0.90),
            ("pistol", "firearm", 0.90),
            ("revolver", "firearm", 0.90),
            ("rifle", "long_gun", 0.92),
            ("shotgun", "long_gun", 0.92),
            ("knife", "knife", 0.92),
            ("blade", "knife", 0.90),
            ("dagger", "knife", 0.90),
            ("machete", "knife", 0.88),
            ("cutter", "knife", 0.80),
            ("weapon", "unknown", 0.62),
            ("sharp object", "unknown", 0.68),
        ]

        for needle, weapon_type, conf in weapon_keywords:
            if needle in text:
                return True, weapon_type, conf

        return False, "unknown", 0.0

    def _scene_hint_from_text(self, text: str) -> str:
        if not text:
            return "unknown"

        if any(k in text for k in ["active attack", "attack", "fighting", "assault", "hostile", "violent"]):
            return "aggressive"
        if any(k in text for k in ["suspicious", "knife", "gun", "weapon", "blade", "sharp object"]):
            return "suspicious"
        if any(k in text for k in ["calm", "peaceful", "quiet", "normal", "uneventful", "typical room", "typical bedroom"]):
            return "normal"
        return "unknown"

    def _is_person_detection(self, det: Any) -> bool:
        if not isinstance(det, dict):
            return True

        cls = det.get("cls", det.get("class_id", det.get("label", det.get("name"))))
        if cls in (0, "0", "person", "Person", "human"):
            return True

        if "bbox" in det or "tlwh" in det or "xyxy" in det:
            return True

        return False

    def _pose_activity_score(self, pose: Any) -> float:
        if pose is None:
            return 0.0

        if isinstance(pose, dict):
            score = 0.0
            for k in ("arms_raised", "reaching_forward", "hands_up", "running", "attacking", "weapon_like_pose"):
                if pose.get(k):
                    score += 0.25
            if score == 0.0:
                score = min(0.15, 0.02 * len(pose))
            return _clamp(score)

        if isinstance(pose, list):
            return _clamp(min(0.2, 0.03 * len(pose)))

        return 0.0

    # ----------------------------------------------------------
    # Frame-level features
    # ----------------------------------------------------------
    def _detect_frame(self, frame) -> list:
        if frame is None or self.detector is None:
            return []

        for method_name in ("detect", "predict", "__call__"):
            method = getattr(self.detector, method_name, None)
            if callable(method):
                try:
                    out = method(frame)
                    return self._normalize_sequence(out)
                except Exception:
                    continue
        return []

    def _update_tracks(self, detections: list) -> list:
        if self.tracker is None:
            return detections

        for method_name in ("update", "update_tracks", "__call__"):
            method = getattr(self.tracker, method_name, None)
            if callable(method):
                try:
                    out = method(detections)
                    normalized = self._normalize_sequence(out)
                    return normalized if normalized else detections
                except Exception:
                    continue
        return detections

    def _estimate_pose(self, frame) -> dict:
        if frame is None or self.pose_estimator is None:
            return {}

        for method_name in ("estimate", "infer", "predict"):
            method = getattr(self.pose_estimator, method_name, None)
            if callable(method):
                try:
                    out = method(frame)
                    return out if isinstance(out, dict) else {"pose": out}
                except Exception:
                    continue
        return {}

    # ----------------------------------------------------------
    # Sensor scoring
    # ----------------------------------------------------------
    def _sensor_context(self, sensor_data: Dict[str, Any] | None) -> Dict[str, Any]:
        sensor_data = sensor_data or {}
        adxl = sensor_data.get("adxl") or {}
        fsr = sensor_data.get("fsr") or {}

        mag = abs(_to_float(adxl.get("magnitude", 0.0)))
        accel_delta = abs(mag - 1.0)

        raw = max(0.0, _to_float(fsr.get("raw", 0.0)))
        force = max(0.0, _to_float(fsr.get("force_g", 0.0)))
        resistance = max(0.0, _to_float(fsr.get("resistance", 0.0)))

        if accel_delta >= 0.75:
            motion_score = 0.95
        elif accel_delta >= 0.40:
            motion_score = 0.75
        elif accel_delta >= 0.18:
            motion_score = 0.50
        elif accel_delta >= 0.08:
            motion_score = 0.25
        else:
            motion_score = 0.05

        if force >= 5000 or raw >= 3500 or resistance <= 1000:
            pressure_score = 0.95
        elif force >= 2000 or raw >= 2500:
            pressure_score = 0.75
        elif force >= 500 or raw >= 800:
            pressure_score = 0.45
        elif raw > 0 or force > 0:
            pressure_score = 0.15
        else:
            pressure_score = 0.0

        sensor_score = _clamp(0.70 * motion_score + 0.60 * pressure_score)
        if motion_score > 0.60 and pressure_score > 0.35:
            sensor_score = _clamp(sensor_score + 0.15)
        elif pressure_score > 0.70:
            sensor_score = _clamp(sensor_score + 0.10)

        sensor_alert = pressure_score >= 0.45 or motion_score >= 0.75
        motion_alert = motion_score >= 0.50
        pressure_alert = pressure_score >= 0.45
        sensor_combo = motion_alert and pressure_alert

        return {
            "raw": {
                "adxl": adxl,
                "fsr": fsr,
            },
            "normalized": {
                "adxl": {
                    "x": _to_float(adxl.get("x", 0.0)),
                    "y": _to_float(adxl.get("y", 0.0)),
                    "z": _to_float(adxl.get("z", 0.0)),
                    "magnitude": mag,
                    "accel_delta": accel_delta,
                },
                "fsr": {
                    "raw": raw,
                    "resistance": resistance,
                    "force_g": force,
                },
            },
            "motion_score": motion_score,
            "pressure_score": pressure_score,
            "sensor_score": sensor_score,
            "sensor_alert": sensor_alert,
            "motion_alert": motion_alert,
            "pressure_alert": pressure_alert,
            "sensor_combo": sensor_combo,
        }

    # ----------------------------------------------------------
    # Audio
    # ----------------------------------------------------------
    def _analyze_audio(self, audio) -> dict:
        if audio is None or self.htsat is None:
            return {
                "threat_score": 0.0,
                "confidence": 0.0,
                "audio_features": [],
                "sound_type_scores": {},
                "audio_events": [],
                "dominant_sound_type": "silence",
                "dominant_sound_confidence": 0.0,
                "summary": "audio unavailable",
            }

        try:
            if hasattr(self.htsat, "submit") and hasattr(self.htsat, "poll"):
                self.htsat.submit(audio)
                audio_features = self.htsat.poll() or []
            else:
                audio_features = []

            if isinstance(audio_features, dict):
                audio_features = [audio_features]
            if not isinstance(audio_features, list):
                audio_features = []

            labels = {
                "silence": 0.0,
                "whispering": 0.0,
                "speaking": 0.0,
                "crowd_murmur": 0.0,
                "footsteps": 0.0,
                "banging": 0.0,
                "impact": 0.0,
                "shouting": 0.0,
                "scream": 0.0,
                "metal_clash": 0.0,
                "gunshot": 0.0,
                "gunfire": 0.0,
                "explosion": 0.0,
            }

            legacy_metallic = 0.0
            legacy_shout = 0.0
            legacy_speech = 0.0
            legacy_footsteps = 0.0
            audio_conf = 0.0

            for item in audio_features:
                if not isinstance(item, dict):
                    continue

                ss = item.get("sound_type_scores")
                if isinstance(ss, dict):
                    for k, v in ss.items():
                        if k in labels:
                            labels[k] = max(labels[k], _to_float(v))

                dom = item.get("dominant_sound_type")
                dom_conf = _to_float(item.get("dominant_sound_confidence", item.get("confidence", item.get("threat_score", 0.0))))
                if isinstance(dom, str) and dom in labels:
                    labels[dom] = max(labels[dom], dom_conf)

                events = item.get("audio_events") or item.get("events")
                if isinstance(events, list):
                    for ev in events:
                        if isinstance(ev, str) and ev in labels:
                            labels[ev] = max(labels[ev], 0.55)
                        elif isinstance(ev, dict):
                            et = ev.get("sound_type", ev.get("type"))
                            ec = _to_float(ev.get("confidence", 0.0))
                            if isinstance(et, str) and et in labels:
                                labels[et] = max(labels[et], ec)

                legacy_metallic = max(legacy_metallic, _to_float(item.get("metallic", 0.0)))
                legacy_shout = max(legacy_shout, _to_float(item.get("shout", 0.0)))
                legacy_speech = max(legacy_speech, _to_float(item.get("speech", 0.0)))
                legacy_footsteps = max(legacy_footsteps, _to_float(item.get("footsteps", 0.0)))
                audio_conf = max(audio_conf, _to_float(item.get("confidence", item.get("threat_score", 0.0))))

            labels["metal_clash"] = max(labels["metal_clash"], legacy_metallic)
            labels["shouting"] = max(labels["shouting"], legacy_shout)
            labels["speaking"] = max(labels["speaking"], legacy_speech)
            labels["footsteps"] = max(labels["footsteps"], legacy_footsteps)

            dominant_sound_type = max(labels, key=labels.get) if labels else "silence"
            dominant_sound_confidence = float(labels.get(dominant_sound_type, 0.0))

            danger_score = max(
                labels["gunshot"] * 1.0,
                labels["gunfire"] * 1.0,
                labels["explosion"] * 1.0,
                labels["metal_clash"] * 0.92,
                labels["scream"] * 0.98,
                labels["shouting"] * 0.86,
                labels["impact"] * 0.74,
                labels["banging"] * 0.68,
            )

            presence_score = max(
                labels["footsteps"] * 0.20,
                labels["speaking"] * 0.06,
                labels["whispering"] * 0.03,
                labels["crowd_murmur"] * 0.05,
            )

            if dominant_sound_type == "silence" and dominant_sound_confidence >= 0.80:
                threat_score = 0.0
            else:
                if dominant_sound_type in {"whispering", "speaking", "crowd_murmur"}:
                    threat_score = max(presence_score, danger_score * 0.20, audio_conf * 0.10)
                elif dominant_sound_type in {"footsteps"}:
                    threat_score = max(presence_score, danger_score * 0.50, audio_conf * 0.20)
                else:
                    threat_score = max(danger_score, presence_score, audio_conf)

            threat_score = _clamp(threat_score)

            audio_events = [
                {"sound_type": k, "confidence": float(v)}
                for k, v in sorted(labels.items(), key=lambda kv: kv[1], reverse=True)
                if v >= 0.20 and k != "silence"
            ]

            return {
                "threat_score": threat_score,
                "confidence": max(threat_score, audio_conf),
                "audio_features": audio_features,
                "sound_type_scores": labels,
                "audio_events": audio_events,
                "dominant_sound_type": dominant_sound_type,
                "dominant_sound_confidence": dominant_sound_confidence,
                "speech_alert": labels["speaking"] >= 0.45 or labels["whispering"] >= 0.55,
                "footstep_alert": labels["footsteps"] >= 0.40,
                "danger_alert": labels["shouting"] >= 0.45 or labels["scream"] >= 0.35 or labels["metal_clash"] >= 0.35 or labels["impact"] >= 0.40 or labels["gunshot"] >= 0.25 or labels["gunfire"] >= 0.25 or labels["explosion"] >= 0.25,
                "metallic": labels["metal_clash"],
                "shout": labels["shouting"],
                "speech": max(labels["speaking"], labels["whispering"], labels["crowd_murmur"]),
                "footsteps": labels["footsteps"],
                "audio_description": f"dominant sound: {dominant_sound_type}",
                "summary": f"dominant sound: {dominant_sound_type}",
            }
        except Exception as exc:
            return {
                "threat_score": 0.0,
                "confidence": 0.0,
                "audio_features": [],
                "sound_type_scores": {},
                "audio_events": [],
                "dominant_sound_type": "silence",
                "dominant_sound_confidence": 0.0,
                "summary": f"audio inference failed: {exc}",
            }

    # ----------------------------------------------------------
    # VLM
    # ----------------------------------------------------------
    def _analyze_vlm(self, frames) -> dict:
        if self.vlm is None:
            return {
                "weapon_present": False,
                "weapon_type": "unknown",
                "scene_intent": "unknown",
                "group_intent": "unknown",
                "confidence": 0.0,
                "raw_text": "",
                "summary": "vlm unavailable",
            }

        frame_list = frames or []
        if not isinstance(frame_list, list):
            frame_list = list(frame_list) if frame_list is not None else []

        if len(frame_list) == 0:
            return {
                "weapon_present": False,
                "weapon_type": "unknown",
                "scene_intent": "unknown",
                "group_intent": "unknown",
                "confidence": 0.0,
                "raw_text": "",
                "summary": "no frames provided",
            }

        keyframes = sample_keyframes(frame_list, k=6)
        last_frame = frame_list[-1]

        raw_text = ""
        parsed = None

        try:
            if hasattr(self.vlm, "infer_video"):
                raw_text = self.vlm.infer_video(keyframes, VIDEO_ANALYSIS_PROMPT)
            elif hasattr(self.vlm, "infer_image"):
                raw_text = self.vlm.infer_image(last_frame, FULL_FRAME_PROMPT)
            else:
                raw_text = ""
        except Exception as exc:
            return {
                "weapon_present": False,
                "weapon_type": "unknown",
                "scene_intent": "unknown",
                "group_intent": "unknown",
                "confidence": 0.0,
                "raw_text": "",
                "summary": f"vlm inference failed: {exc}",
            }

        if isinstance(raw_text, str) and raw_text.strip():
            parsed = parse_vlm_json(raw_text)

        if isinstance(parsed, dict):
            weapon_present = bool(parsed.get("weapon_present")) or str(parsed.get("weapon_type", "none")).lower() not in {"none", "", "unknown"}
            weapon_type = str(parsed.get("weapon_type", parsed.get("weapon", "unknown"))).lower()
            confidence = _clamp(
                _to_float(
                    parsed.get(
                        "confidence",
                        parsed.get("weapon_confidence", parsed.get("threat_score", 0.0))
                    )
                )
            )

            scene_intent = self._pick_text(
                parsed,
                ("scene_intent", "scene", "intent", "summary", "description"),
                default="unknown",
            )
            group_intent = self._pick_text(
                parsed,
                ("group_intent", "group", "intent", "summary", "description"),
                default=scene_intent,
            )

            text_blob = self._text_blob({
                "raw_text": raw_text,
                **parsed
            })
            text_weapon_present, text_weapon_type, text_weapon_conf = self._weapon_hint_from_text(text_blob)
            text_scene_hint = self._scene_hint_from_text(text_blob)

            if text_weapon_present:
                weapon_present = True
                if weapon_type in {"unknown", "", "none"}:
                    weapon_type = text_weapon_type
                confidence = max(confidence, text_weapon_conf)

            if text_scene_hint in {"suspicious", "aggressive"} and scene_intent in {"unknown", "normal", "calm"}:
                scene_intent = text_scene_hint
            if text_weapon_present and group_intent in {"unknown", "normal", "calm"}:
                group_intent = "suspicious"

            return {
                **parsed,
                "raw_text": raw_text,
                "weapon_present": weapon_present,
                "weapon_type": weapon_type,
                "scene_intent": scene_intent,
                "group_intent": group_intent,
                "confidence": confidence,
            }

        text_blob = self._text_blob({"raw_text": raw_text})
        weapon_present, weapon_type, weapon_conf = self._weapon_hint_from_text(text_blob)
        scene_hint = self._scene_hint_from_text(text_blob)

        return {
            "weapon_present": weapon_present,
            "weapon_type": weapon_type,
            "scene_intent": scene_hint,
            "group_intent": scene_hint if scene_hint != "unknown" else "unknown",
            "confidence": weapon_conf if weapon_present else 0.0,
            "raw_text": raw_text if isinstance(raw_text, str) else "",
            "summary": "vlm inference failed",
        }

    # ----------------------------------------------------------
    # Vision scoring
    # ----------------------------------------------------------
    def _vision_score(self, frame_stats: List[Dict[str, Any]], vlm_result: Dict[str, Any]) -> tuple[float, dict]:
        scene_intent = str(vlm_result.get("scene_intent", "unknown")).lower()
        group_intent = str(vlm_result.get("group_intent", "unknown")).lower()
        weapon_present = bool(vlm_result.get("weapon_present"))
        weapon_type = str(vlm_result.get("weapon_type", "unknown")).lower()
        weapon_conf = _clamp(
            max(
                _to_float(vlm_result.get("confidence", 0.0)),
                _to_float(vlm_result.get("weapon_confidence", 0.0)),
                _to_float(vlm_result.get("threat_score", 0.0)),
            )
        )

        people_counts = [float(s.get("people", 0.0)) for s in frame_stats] or [0.0]
        track_counts = [float(s.get("tracks", 0.0)) for s in frame_stats] or [0.0]
        pose_scores = [float(s.get("pose_score", 0.0)) for s in frame_stats] or [0.0]

        avg_people = sum(people_counts) / max(1, len(people_counts))
        peak_people = max(people_counts)
        avg_tracks = sum(track_counts) / max(1, len(track_counts))
        peak_tracks = max(track_counts)
        avg_pose = sum(pose_scores) / max(1, len(pose_scores))
        pose_peak = max(pose_scores)

        crowd_score = _clamp(
            0.18 * min(avg_people / 3.0, 1.0) +
            0.14 * min(peak_people / 8.0, 1.0) +
            0.12 * min(avg_tracks / 4.0, 1.0) +
            0.08 * min(peak_tracks / 12.0, 1.0)
        )

        activity_score = _clamp(
            0.30 * avg_pose +
            0.15 * pose_peak +
            crowd_score
        )

        if scene_intent in {"normal", "calm", "peaceful"} and not weapon_present:
            scene_base = 0.04
        elif scene_intent in {"suspicious"}:
            scene_base = 0.38
        elif scene_intent in {"aggressive", "hostile", "threatening"}:
            scene_base = 0.68
        else:
            scene_base = 0.12

        weapon_score = 0.0
        if weapon_present:
            weapon_score = 0.60 + 0.28 * weapon_conf
            if weapon_type in {"knife", "blade", "dagger", "cutter", "gun", "firearm", "long_gun", "rifle", "shotgun"}:
                weapon_score += 0.20
            elif weapon_type in {"tool", "stick"}:
                weapon_score += 0.06
            else:
                weapon_score += 0.10

        text_blob = self._text_blob(vlm_result)
        text_weapon_present, _, text_weapon_conf = self._weapon_hint_from_text(text_blob)
        if text_weapon_present:
            weapon_score = max(weapon_score, 0.58 + 0.32 * text_weapon_conf)
            weapon_present = True

        if scene_intent == "suspicious" and weapon_present:
            scene_base = max(scene_base, 0.72)

        if scene_intent in {"aggressive", "hostile", "threatening"} and weapon_present:
            scene_base = max(scene_base, 0.82)

        if scene_intent in {"normal", "calm", "peaceful"} and not weapon_present:
            if avg_people >= 5 or peak_people >= 5:
                scene_base = max(scene_base, 0.15 + 0.02 * min(avg_people, 10.0))
            else:
                scene_base = min(scene_base, 0.10)

        raw_vision = max(
            scene_base,
            0.55 * scene_base + 0.45 * activity_score,
            0.50 * scene_base + 0.50 * weapon_score,
            activity_score,
            weapon_score,
        )

        if group_intent in {"hostile", "coordinated", "surrounding"}:
            raw_vision = max(raw_vision, 0.35 + 0.10 * weapon_conf)

        if weapon_present:
            raw_vision = max(raw_vision, 0.62)

        if scene_intent == "suspicious" and weapon_present:
            raw_vision = max(raw_vision, 0.78)

        details = {
            "avg_people": avg_people,
            "peak_people": peak_people,
            "avg_tracks": avg_tracks,
            "peak_tracks": peak_tracks,
            "crowd_score": crowd_score,
            "activity_score": activity_score,
            "scene_base": scene_base,
            "weapon_score": weapon_score,
            "weapon_present": weapon_present,
            "weapon_type": weapon_type,
            "weapon_conf": weapon_conf,
        }

        return _clamp(raw_vision), details

    # ----------------------------------------------------------
    # Main entry point
    # ----------------------------------------------------------
    def analyze_burst(self, frames, audio, sensor_data=None):
        sensor_context = self._sensor_context(sensor_data)

        frame_stats = []
        for frame in frames or []:
            detections = self._detect_frame(frame)
            person_dets = [d for d in detections if self._is_person_detection(d)]
            tracks = self._update_tracks(person_dets)
            pose = self._estimate_pose(frame)

            frame_stats.append({
                "people": len(person_dets) if person_dets else len(tracks),
                "tracks": len(tracks),
                "pose_score": self._pose_activity_score(pose),
                "pose": pose,
            })

        audio_result = self._analyze_audio(audio)
        vlm_result = self._analyze_vlm(frames)

        vision_score, vision_details = self._vision_score(frame_stats, vlm_result)
        audio_score = _clamp(_to_float(audio_result.get("threat_score", 0.0)))

        if str(audio_result.get("dominant_sound_type", "")).lower() == "silence":
            audio_score = 0.0

        sensor_score = _clamp(_to_float(sensor_context.get("sensor_score", 0.0)))

        final_score = 0.40 * vision_score + 0.30 * audio_score + 0.30 * sensor_score

        weapon_present = bool(vlm_result.get("weapon_present"))
        weapon_conf = _clamp(
            max(
                _to_float(vlm_result.get("confidence", 0.0)),
                _to_float(vlm_result.get("weapon_confidence", 0.0)),
                _to_float(vlm_result.get("threat_score", 0.0)),
            )
        )

        if weapon_present:
            final_score += 0.18 + 0.12 * weapon_conf

        dangerous_audio = str(audio_result.get("dominant_sound_type", "")).lower()
        if dangerous_audio in {"shouting", "scream", "metal_clash", "impact", "banging", "gunshot", "gunfire", "explosion"}:
            final_score += 0.10 + 0.10 * audio_score
        elif dangerous_audio in {"footsteps"}:
            final_score += 0.02 * audio_score
        elif dangerous_audio == "silence":
            final_score -= 0.08

        if sensor_context.get("sensor_combo"):
            final_score += 0.10
        elif sensor_context.get("pressure_alert"):
            final_score += 0.05
        elif sensor_context.get("motion_alert"):
            final_score += 0.03

        normal_scene = str(vlm_result.get("scene_intent", "unknown")).lower() in {"normal", "calm", "peaceful"} and not weapon_present
        if normal_scene:
            avg_people = vision_details.get("avg_people", 0.0)
            peak_people = vision_details.get("peak_people", 0.0)
            if avg_people <= 1.0 and peak_people <= 1.0 and dangerous_audio == "silence":
                final_score = min(final_score, 0.12)
            elif avg_people >= 5 or peak_people >= 5:
                final_score = min(final_score, 0.35)
            else:
                final_score = min(final_score, 0.22)

        final_score = _clamp(final_score)

        if final_score < 0.18:
            threat_level = 1
        elif final_score < 0.35:
            threat_level = 2
        elif final_score < 0.55:
            threat_level = 3
        elif final_score < 0.75:
            threat_level = 4
        else:
            threat_level = 5

        scene_intent = self._pick_text(
            vlm_result,
            ("scene_intent", "intent", "label", "summary", "description"),
            default="unknown",
        )
        group_intent = self._pick_text(
            vlm_result,
            ("group_intent", "intent", "label"),
            default=scene_intent,
        )

        briefing = self._pick_text(
            vlm_result,
            ("briefing", "description", "summary", "raw_text"),
            default="",
        )
        if not briefing:
            briefing = (
                f"vision={vision_score:.2f}, audio={audio_score:.2f}, sensor={sensor_score:.2f}, "
                f"threat_level={threat_level}"
            )

        decision = "threat" if threat_level >= 3 else "safe"

        audit = {
            "vision_score": vision_score,
            "audio_score": audio_score,
            "sensor_score": sensor_score,
            "final_score": final_score,
            "detection_count": int(sum(s["people"] for s in frame_stats)),
            "track_count": int(sum(s["tracks"] for s in frame_stats)),
            "avg_people": vision_details.get("avg_people", 0.0),
            "peak_people": vision_details.get("peak_people", 0.0),
            "avg_tracks": vision_details.get("avg_tracks", 0.0),
            "peak_tracks": vision_details.get("peak_tracks", 0.0),
            "crowd_score": vision_details.get("crowd_score", 0.0),
            "activity_score": vision_details.get("activity_score", 0.0),
            "scene_base": vision_details.get("scene_base", 0.0),
            "weapon_score": vision_details.get("weapon_score", 0.0),
            "sensor_motion_score": sensor_context.get("motion_score", 0.0),
            "sensor_pressure_score": sensor_context.get("pressure_score", 0.0),
            "sensor_adxl_magnitude": sensor_context.get("normalized", {}).get("adxl", {}).get("magnitude", 0.0),
            "sensor_fsr_force_g": sensor_context.get("normalized", {}).get("fsr", {}).get("force_g", 0.0),
            "sensor_fsr_raw": sensor_context.get("normalized", {}).get("fsr", {}).get("raw", 0.0),
        }

        return {
            "threat_level": threat_level,
            "confidence": final_score,
            "group_intent": group_intent,
            "scene_intent": scene_intent,
            "decision": decision,
            "briefing": briefing,
            "actors": [s for s in frame_stats if s.get("people", 0) > 0],
            "video_context": {
                "pose": frame_stats[-1]["pose"] if frame_stats else {},
                "audio": audio_result,
                "vision": {
                    "frames": frame_stats,
                },
                "vlm": vlm_result,
                "weapon_present": weapon_present,
            },
            "audit": audit,
            "sensor_data": sensor_data,
            "sensor_context": sensor_context,
            "audio_result": audio_result,
            "vlm_result": vlm_result,
        }