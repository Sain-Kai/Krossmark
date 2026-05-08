def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _max_audio_scores(audio):
    audio = _as_list(audio)

    scores = {
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
    }

    for item in audio:
        if not isinstance(item, dict):
            continue

        ss = item.get("sound_type_scores")
        if isinstance(ss, dict):
            for k, v in ss.items():
                if k in scores:
                    scores[k] = max(scores[k], float(v or 0.0))

        dom = str(item.get("dominant_sound_type", "") or "").lower()
        dom_conf = float(item.get("dominant_sound_confidence", item.get("confidence", item.get("threat_score", 0.0))) or 0.0)
        if dom in scores:
            scores[dom] = max(scores[dom], dom_conf)

        events = item.get("audio_events") or item.get("events")
        if isinstance(events, list):
            for ev in events:
                if isinstance(ev, str) and ev in scores:
                    scores[ev] = max(scores[ev], 0.55)
                elif isinstance(ev, dict):
                    et = str(ev.get("sound_type", ev.get("type", ""))).lower()
                    ec = float(ev.get("confidence", 0.0) or 0.0)
                    if et in scores:
                        scores[et] = max(scores[et], ec)

        scores["metal_clash"] = max(scores["metal_clash"], float(item.get("metallic", 0.0) or 0.0))
        scores["shouting"] = max(scores["shouting"], float(item.get("shout", 0.0) or 0.0))
        scores["speaking"] = max(scores["speaking"], float(item.get("speech", 0.0) or 0.0))
        scores["footsteps"] = max(scores["footsteps"], float(item.get("footsteps", 0.0) or 0.0))

    return scores


def _sensor_context_from_raw(sensor_data):
    sensor_data = sensor_data or {}
    adxl = sensor_data.get("adxl") or {}
    fsr = sensor_data.get("fsr") or {}

    mag = abs(float(adxl.get("magnitude", 0.0) or 0.0))
    accel_delta = abs(mag - 1.0)

    raw = float(fsr.get("raw", 0.0) or 0.0)
    force = float(fsr.get("force_g", 0.0) or 0.0)

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

    if force >= 5000 or raw >= 3500:
        pressure_score = 0.95
    elif force >= 2000 or raw >= 2500:
        pressure_score = 0.75
    elif force >= 500 or raw >= 800:
        pressure_score = 0.45
    elif raw > 0 or force > 0:
        pressure_score = 0.15
    else:
        pressure_score = 0.0

    sensor_score = min(1.0, 0.7 * motion_score + 0.6 * pressure_score)
    sensor_alert = pressure_score >= 0.45 or motion_score >= 0.75
    sensor_combo = motion_score >= 0.35 and pressure_score >= 0.35

    return {
        "raw": {
            "adxl": adxl,
            "fsr": fsr,
        },
        "motion_score": motion_score,
        "pressure_score": pressure_score,
        "sensor_score": sensor_score,
        "sensor_alert": sensor_alert,
        "sensor_combo": sensor_combo,
        "motion_alert": motion_score >= 0.50,
        "pressure_alert": pressure_score >= 0.45,
    }


class ThreatEngine:
    def compute(self, fused, previous_requests=0, sensor_data=None):
        weapon_votes = 0
        aggressive_votes = 0
        total = len(fused["frames"]) or 1

        sensor_context = _sensor_context_from_raw(sensor_data if sensor_data is not None else fused.get("sensor"))

        for e in fused["frames"]:
            for feats in e.get("pose_feats", []):
                if isinstance(feats, dict) and feats.get("arms_raised") and feats.get("reaching_forward"):
                    aggressive_votes += 1

            vlm = e.get("vlm")
            if isinstance(vlm, dict) and (vlm.get("weapon_present") is True or str(vlm.get("weapon_type", "none")).lower() not in {"none", "unknown", ""}):
                weapon_votes += 1

        audio = fused["audio"]
        audio_scores = _max_audio_scores(audio)

        metallic = audio_scores["metal_clash"]
        shout = audio_scores["shouting"]
        scream = audio_scores["scream"]
        footsteps = audio_scores["footsteps"]
        speaking = audio_scores["speaking"]
        whispering = audio_scores["whispering"]

        weapon_strength = weapon_votes / max(1, total)
        aggression_strength = aggressive_votes / max(1, total)
        sensor_strength = sensor_context.get("sensor_score", 0.0)
        sensor_alert = sensor_context.get("sensor_alert", False)
        sensor_combo = sensor_context.get("sensor_combo", False)

        audio_strength = max(metallic, shout, scream, footsteps, speaking, whispering)

        threat = 1

        if weapon_strength > 0.12 or aggression_strength > 0.28:
            threat = 2

        if weapon_strength > 0.22 or shout > 0.45 or scream > 0.35 or metallic > 0.35:
            threat = max(threat, 3)

        if weapon_strength > 0.35 or metallic > 0.55 or shout > 0.55 or scream > 0.45:
            threat = max(threat, 4)

        if weapon_strength > 0.35 and (metallic > 0.45 or shout > 0.45 or scream > 0.45):
            threat = max(threat, 5)

        if sensor_alert and (weapon_strength > 0.15 or aggression_strength > 0.15 or audio_strength > 0.35):
            threat = max(threat, 3)

        if sensor_combo and (weapon_strength > 0.22 or shout > 0.35 or metallic > 0.35):
            threat = max(threat, 4)

        if sensor_strength > 0.60 and (weapon_strength > 0.22 or metallic > 0.35 or shout > 0.35 or scream > 0.35):
            threat = max(threat, 5)

        confidence = min(
            1.0,
            0.22
            + 0.35 * weapon_strength
            + 0.20 * aggression_strength
            + 0.20 * audio_strength
            + 0.18 * sensor_strength
        )

        if threat >= 4 and confidence >= 0.65:
            decision = "CONFIRM_THREAT"
        elif confidence < 0.45:
            decision = "REQUEST_MORE_DATA" if previous_requests == 0 else "DISMISS_FALSE_TRIGGER"
        else:
            decision = "REQUEST_MORE_DATA"

        return {
            "decision": decision,
            "threat_level": threat,
            "confidence": round(confidence, 2),
            "sensor_context": sensor_context,
            "audio_context": audio_scores,
        }