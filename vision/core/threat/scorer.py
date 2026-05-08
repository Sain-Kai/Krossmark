from vision.core.intent.states import PersonIntent


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _max_score_from_audio_features(audio_features):
    audio_features = _as_list(audio_features)

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

    for item in audio_features:
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

        # Legacy compatibility
        scores["metal_clash"] = max(scores["metal_clash"], float(item.get("metallic", 0.0) or 0.0))
        scores["shouting"] = max(scores["shouting"], float(item.get("shout", 0.0) or 0.0))
        scores["speaking"] = max(scores["speaking"], float(item.get("speech", 0.0) or 0.0))
        scores["footsteps"] = max(scores["footsteps"], float(item.get("footsteps", 0.0) or 0.0))

    return scores


class DefenseThreatScorer:
    def score(self,
              person_intents,
              group_intent,
              scene_intent,
              weapon_states,
              audio_features,
              video_context,
              sensor_data=None):

        person_intents = _as_list(person_intents)
        weapon_states = _as_list(weapon_states)
        audio_features = _as_list(audio_features)

        confirmed_weapon = any(
            ws and (
                ws.get("confirmed") or
                str(ws.get("weapon", "none")).lower() not in ["none", "unknown", ""]
            )
            for ws in weapon_states
            if isinstance(ws, dict)
        )

        suspicious_weapon = any(
            ws and str(ws.get("weapon", "none")).lower() not in ["none", "unknown", ""]
            for ws in weapon_states
            if isinstance(ws, dict)
        )

        hostile = any(
            p in [PersonIntent.AGGRESSIVE, PersonIntent.ATTACKING]
            for p in person_intents
        )

        coordinated = str(group_intent).upper().endswith("COORDINATED") or str(group_intent).lower() in {"coordinated", "hostile", "surrounding"}

        audio_scores = _max_score_from_audio_features(audio_features)

        whispering = audio_scores["whispering"]
        speaking = audio_scores["speaking"]
        footsteps = audio_scores["footsteps"]
        shouting = audio_scores["shouting"]
        scream = audio_scores["scream"]
        metal_clash = audio_scores["metal_clash"]
        banging = audio_scores["banging"]
        impact = audio_scores["impact"]

        audio_alert = (
            shouting > 0.45 or
            scream > 0.35 or
            metal_clash > 0.35 or
            banging > 0.40 or
            impact > 0.45
        )

        speech_alert = speaking > 0.45 or whispering > 0.55
        footstep_alert = footsteps > 0.40

        global_weapon_alert = bool(video_context and video_context.get("weapon_present") is True)
        scene_aggressive = str(scene_intent).lower() in {"aggressive", "hostile", "threatening"}
        scene_suspicious = str(scene_intent).lower() in {"suspicious", "unknown"}

        # Sensor scoring (lightweight and robust)
        sensor = sensor_data or {}
        adxl = sensor.get("adxl") or {}
        fsr = sensor.get("fsr") or {}
        mag = abs(float(adxl.get("magnitude", 0.0) or 0.0))
        accel_delta = abs(mag - 1.0)
        raw = float(fsr.get("raw", 0.0) or 0.0)
        force = float(fsr.get("force_g", 0.0) or 0.0)

        motion_score = 0.05
        if accel_delta >= 0.75:
            motion_score = 0.95
        elif accel_delta >= 0.40:
            motion_score = 0.75
        elif accel_delta >= 0.18:
            motion_score = 0.50
        elif accel_delta >= 0.08:
            motion_score = 0.25

        pressure_score = 0.0
        if force >= 5000 or raw >= 3500:
            pressure_score = 0.95
        elif force >= 2000 or raw >= 2500:
            pressure_score = 0.75
        elif force >= 500 or raw >= 800:
            pressure_score = 0.45
        elif raw > 0 or force > 0:
            pressure_score = 0.15

        sensor_strength = min(1.0, 0.7 * motion_score + 0.6 * pressure_score)
        sensor_alert = pressure_score >= 0.45 or motion_score >= 0.75
        sensor_pressure = pressure_score >= 0.45

        # LEVEL 1 – NORMAL
        if (
            not hostile
            and not coordinated
            and not confirmed_weapon
            and not global_weapon_alert
            and not sensor_alert
            and not audio_alert
            and not scene_aggressive
        ):
            conf = min(0.45, 0.30 + 0.10 * sensor_strength + 0.06 * max(speaking, whispering))
            return 1, round(conf, 2)

        # LEVEL 2 – LOW / SUSPICIOUS
        if (
            footstep_alert or
            speech_alert or
            suspicious_weapon or
            coordinated or
            scene_suspicious or
            motion_score >= 0.25
        ) and not confirmed_weapon and not audio_alert:
            conf = min(0.58, 0.40 + 0.12 * sensor_strength + 0.08 * max(footsteps, speaking, whispering))
            return 2, round(conf, 2)

        # LEVEL 3 – WATCH / PREPARE
        if (
            global_weapon_alert or
            hostile or
            sensor_alert or
            audio_alert or
            scene_aggressive
        ) and not confirmed_weapon:
            conf = min(0.75, 0.55 + 0.12 * sensor_strength + 0.12 * max(shouting, metal_clash, scream))
            return 3, round(conf, 2)

        # LEVEL 4 – ARMED INTRUSION / HIGH RISK
        if confirmed_weapon and (hostile or coordinated or sensor_strength >= 0.35 or audio_alert or global_weapon_alert):
            conf = min(0.88, 0.70 + 0.15 * sensor_strength + 0.10 * max(shouting, metal_clash, scream))
            return 4, round(conf, 2)

        # LEVEL 5 – ACTIVE ATTACK
        if confirmed_weapon and hostile and (audio_alert or sensor_pressure or sensor_strength >= 0.45):
            conf = min(0.96, 0.84 + 0.08 * sensor_strength + 0.08 * max(shouting, metal_clash, scream))
            return 5, round(conf, 2)

        return 2, round(min(0.60, 0.42 + 0.10 * sensor_strength + 0.08 * max(footsteps, speaking, whispering)), 2)