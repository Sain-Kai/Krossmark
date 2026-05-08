import math


class BayesianThreatScorer:
    def __init__(self):
        self.prior = 0.05

        self.likelihoods = {
            # Visual / behavioral
            "aggressive_behavior": 6.0,
            "coordinated_activity": 4.0,
            "high_speed": 2.0,

            # Audio semantic signals
            "audio_whispering": 1.08,
            "audio_speaking": 1.05,
            "audio_crowd_murmur": 1.15,
            "audio_footsteps": 2.0,
            "audio_banging": 3.2,
            "audio_impact": 3.6,
            "audio_shouting": 4.8,
            "audio_scream": 5.5,
            "audio_metal_clash": 6.0,

            # Sensor signals
            "sensor_alert": 3.2,
            "sensor_motion": 2.2,
            "sensor_pressure": 2.8,
            "sensor_combo": 4.0,
        }

        self.weapon_base_likelihood = 12.0
        self.sensor_base_likelihood = 3.0

    def _log_odds(self, p):
        return math.log(p / (1 - p))

    def _from_log_odds(self, lo):
        odds = math.exp(lo)
        return odds / (1 + odds)

    def _apply_soft_likelihood(self, log_odds, likelihood_ratio, strength):
        strength = max(0.0, min(1.0, float(strength)))
        if likelihood_ratio <= 1.0 or strength <= 0.0:
            return log_odds
        scaled = 1.0 + (likelihood_ratio - 1.0) * strength
        return log_odds + math.log(max(scaled, 1e-6))

    def _audio_strengths(self, evidence):
        strengths = {}

        sound_scores = evidence.get("sound_type_scores")
        if isinstance(sound_scores, dict):
            for k, v in sound_scores.items():
                strengths[f"audio_{k}"] = max(0.0, min(1.0, float(v or 0.0)))

        dominant = str(evidence.get("dominant_sound_type", "") or evidence.get("audio_event", "")).lower()
        dominant_conf = float(
            evidence.get(
                "dominant_sound_confidence",
                evidence.get("audio_score", evidence.get("confidence", 0.0))
            ) or 0.0
        )

        if dominant:
            strengths[f"audio_{dominant}"] = max(strengths.get(f"audio_{dominant}", 0.0), min(1.0, dominant_conf))

        audio_events = evidence.get("audio_events")
        if isinstance(audio_events, list):
            for ev in audio_events:
                if isinstance(ev, str):
                    strengths[f"audio_{ev.lower()}"] = max(strengths.get(f"audio_{ev.lower()}", 0.0), 0.55)
                elif isinstance(ev, dict):
                    et = str(ev.get("sound_type", ev.get("type", ""))).lower()
                    ec = float(ev.get("confidence", 0.0) or 0.0)
                    if et:
                        strengths[f"audio_{et}"] = max(strengths.get(f"audio_{et}", 0.0), min(1.0, ec))

        # Legacy fields
        if evidence.get("audio_spike"):
            strengths["audio_shouting"] = max(strengths.get("audio_shouting", 0.0), 0.5)

        return strengths

    def score(self, evidence):
        evidence = evidence or {}
        log_odds = self._log_odds(self.prior)

        # Weapon handling
        weapon_severity = float(evidence.get("weapon_severity", 0.0) or 0.0)
        weapon_present = bool(evidence.get("weapon_present")) or weapon_severity > 0.0
        weapon_type = str(evidence.get("weapon_type", "") or "").lower()

        if weapon_present:
            severity = max(weapon_severity, 0.5 if weapon_type and weapon_type != "none" else 0.35)
            scaled_lr = self.weapon_base_likelihood ** severity
            if weapon_type in {"knife", "blade", "dagger", "cutter"}:
                scaled_lr *= 1.20
            elif weapon_type in {"firearm", "gun", "long_gun", "rifle", "shotgun"}:
                scaled_lr *= 1.45
            log_odds += math.log(max(scaled_lr, 1e-6))

        # Sensor handling
        sensor_score = float(evidence.get("sensor_score", 0.0) or 0.0)
        if sensor_score > 0:
            sensor_lr = 1.0 + (self.sensor_base_likelihood - 1.0) * min(sensor_score * 1.25, 1.0)
            log_odds += math.log(max(sensor_lr, 1e-6))

        # Audio handling
        audio_strengths = self._audio_strengths(evidence)

        audio_lr_map = {
            "audio_whispering": 1.06,
            "audio_speaking": 1.04,
            "audio_crowd_murmur": 1.15,
            "audio_footsteps": 1.90,
            "audio_banging": 3.10,
            "audio_impact": 3.60,
            "audio_shouting": 4.60,
            "audio_scream": 5.20,
            "audio_metal_clash": 6.00,
        }

        for key, strength in audio_strengths.items():
            if key in audio_lr_map:
                log_odds = self._apply_soft_likelihood(log_odds, audio_lr_map[key], strength)

        # Generic high-level evidence flags
        for key, present in evidence.items():
            if key in {"weapon_severity", "sensor_score", "weapon_present", "weapon_type", "sound_type_scores", "audio_events", "dominant_sound_type", "dominant_sound_confidence", "audio_score", "confidence"}:
                continue
            if present and key in self.likelihoods:
                log_odds += math.log(self.likelihoods[key])

        probability = self._from_log_odds(log_odds)

        if probability < 0.12:
            level = 1
        elif probability < 0.28:
            level = 2
        elif probability < 0.48:
            level = 3
        elif probability < 0.72:
            level = 4
        else:
            level = 5

        return level, round(probability, 3)