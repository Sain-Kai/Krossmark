import numpy as np
import torch
import torch.nn.functional as F
from transformers import ClapModel, ClapProcessor


class HTSATWorker:
    """
    CLAP-based audio worker with zero-shot sound-type scoring.

    Output includes:
    - sound_type_scores
    - dominant_sound_type
    - dominant_sound_confidence
    - audio_events
    - audio_description
    - threat_score
    - legacy fields: metallic, shout, speech, footsteps
    """

    def __init__(self, model_path):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        self.model = ClapModel.from_pretrained(model_path).to(self.device)
        self.processor = ClapProcessor.from_pretrained(model_path)

        self._result = []

        self.label_prompts = {
            "silence": "silence or a very quiet room",
            "whispering": "a person whispering softly",
            "speaking": "a person speaking in a normal voice",
            "crowd_murmur": "multiple people murmuring softly in a crowd",
            "footsteps": "footsteps walking on a floor",
            "banging": "banging on a door or table",
            "impact": "a loud impact or thud",
            "shouting": "a person shouting loudly",
            "scream": "a person screaming",
            "metal_clash": "metal objects clanging together",
            "gunshot": "a gunshot",
            "gunfire": "gunfire or multiple gunshots",
            "explosion": "an explosion or blast",
        }

    # ----------------------------------------------------------
    # Utils
    # ----------------------------------------------------------
    def _sanitize_audio(self, audio_waveform):
        if audio_waveform is None:
            return None

        audio_waveform = np.asarray(audio_waveform, dtype=np.float32).flatten()
        if audio_waveform.size == 0:
            return None

        audio_waveform = np.nan_to_num(audio_waveform, nan=0.0, posinf=0.0, neginf=0.0)
        return audio_waveform

    def _audio_profile(self, audio_waveform):
        if audio_waveform is None or audio_waveform.size == 0:
            return {
                "rms": 0.0,
                "peak": 0.0,
                "zcr": 0.0,
                "crest_factor": 0.0,
            }

        x = audio_waveform.astype(np.float32)
        rms = float(np.sqrt(np.mean(np.square(x))) + 1e-9)
        peak = float(np.max(np.abs(x)) + 1e-9)

        signs = np.sign(x)
        signs[signs == 0] = 1
        zcr = float(np.mean(np.abs(np.diff(signs)) > 0))

        crest_factor = float(peak / (rms + 1e-9))

        return {
            "rms": rms,
            "peak": peak,
            "zcr": zcr,
            "crest_factor": crest_factor,
        }

    def _heuristic_scores(self, profile):
        rms = profile["rms"]
        peak = profile["peak"]
        zcr = profile["zcr"]
        crest = profile["crest_factor"]

        scores = {k: 0.0 for k in self.label_prompts.keys()}

        # Quiet room: silence should dominate and threat must stay near zero.
        if rms < 0.006 and peak < 0.02:
            scores["silence"] = 0.99
            return scores

        # Soft speech / whisper / crowd
        if rms < 0.018:
            scores["whispering"] = 0.82
            scores["speaking"] = 0.18
            scores["crowd_murmur"] = 0.12
        elif rms < 0.04:
            scores["speaking"] = 0.76
            scores["whispering"] = 0.24
            scores["crowd_murmur"] = 0.20
        elif rms < 0.07:
            scores["speaking"] = 0.58
            scores["footsteps"] = 0.40
            scores["crowd_murmur"] = 0.20
        elif rms < 0.11:
            scores["shouting"] = 0.72
            scores["footsteps"] = 0.30
            scores["impact"] = 0.20
        else:
            scores["shouting"] = 0.86
            scores["scream"] = 0.50
            scores["impact"] = 0.42

        if zcr > 0.12 and rms < 0.04:
            scores["whispering"] = max(scores["whispering"], 0.50)

        if 0.04 <= rms <= 0.12:
            scores["footsteps"] = max(scores["footsteps"], 0.50)

        # Strong transient peaks: impact / metal / gunshot / explosion.
        if peak > 0.22:
            scores["metal_clash"] = max(scores["metal_clash"], 0.40)
            scores["impact"] = max(scores["impact"], 0.45)
            scores["gunshot"] = max(scores["gunshot"], 0.25)
            scores["gunfire"] = max(scores["gunfire"], 0.20)
            scores["explosion"] = max(scores["explosion"], 0.20)

        if peak > 0.35:
            scores["gunshot"] = max(scores["gunshot"], 0.52)
            scores["gunfire"] = max(scores["gunfire"], 0.42)
            scores["explosion"] = max(scores["explosion"], 0.38)
            scores["metal_clash"] = max(scores["metal_clash"], 0.48)
            scores["impact"] = max(scores["impact"], 0.58)

        if crest > 12.0:
            scores["impact"] = max(scores["impact"], 0.36)

        return scores

    def _move_to_device(self, batch):
        out = {}
        for k, v in batch.items():
            if hasattr(v, "to"):
                out[k] = v.to(self.device)
            else:
                out[k] = v
        return out

    def _build_audio_inputs(self, audio_waveform):
        attempts = [
            {"audios": [audio_waveform], "sampling_rate": 48000, "return_tensors": "pt"},
            {"audio": audio_waveform, "sampling_rate": 48000, "return_tensors": "pt"},
            {"audio": [audio_waveform], "sampling_rate": 48000, "return_tensors": "pt"},
        ]
        last_exc = None
        for kwargs in attempts:
            try:
                batch = self.processor(**kwargs)
                return self._move_to_device(batch)
            except Exception as exc:
                last_exc = exc
        raise last_exc

    def _build_text_inputs(self, texts):
        attempts = [
            {"text": texts, "return_tensors": "pt", "padding": True},
            {"texts": texts, "return_tensors": "pt", "padding": True},
        ]
        last_exc = None
        for kwargs in attempts:
            try:
                batch = self.processor(**kwargs)
                return self._move_to_device(batch)
            except Exception as exc:
                last_exc = exc
        raise last_exc

    def _clap_scores(self, audio_waveform):
        labels = list(self.label_prompts.keys())
        texts = [self.label_prompts[k] for k in labels]

        audio_inputs = self._build_audio_inputs(audio_waveform)
        text_inputs = self._build_text_inputs(texts)

        with torch.no_grad():
            audio_emb = self.model.get_audio_features(**audio_inputs)
            text_emb = self.model.get_text_features(**text_inputs)

            if audio_emb.ndim == 1:
                audio_emb = audio_emb.unsqueeze(0)
            if text_emb.ndim == 1:
                text_emb = text_emb.unsqueeze(0)

            audio_emb = F.normalize(audio_emb, dim=-1)
            text_emb = F.normalize(text_emb, dim=-1)

            logits = torch.matmul(audio_emb, text_emb.T).squeeze(0)
            probs = torch.softmax(logits / 0.08, dim=-1)

        return {labels[i]: float(probs[i].item()) for i in range(len(labels))}

    def _combine_scores(self, clap_scores, heuristic_scores):
        if not clap_scores:
            return heuristic_scores

        combined = {}
        for label in self.label_prompts.keys():
            c = float(clap_scores.get(label, 0.0) or 0.0)
            h = float(heuristic_scores.get(label, 0.0) or 0.0)
            combined[label] = float(max(c, h, 0.8 * c + 0.2 * h))
        return combined

    def _threat_from_sound_scores(self, scores, profile, dominant_sound_type):
        rms = profile.get("rms", 0.0)
        peak = profile.get("peak", 0.0)

        # Silence must never become a threat.
        if dominant_sound_type == "silence" or (rms < 0.006 and peak < 0.02):
            return 0.0

        danger = max(
            scores.get("gunshot", 0.0) * 1.0,
            scores.get("gunfire", 0.0) * 1.0,
            scores.get("explosion", 0.0) * 1.0,
            scores.get("metal_clash", 0.0) * 0.90,
            scores.get("scream", 0.0) * 0.90,
            scores.get("shouting", 0.0) * 0.85,
            scores.get("impact", 0.0) * 0.70,
            scores.get("banging", 0.0) * 0.60,
        )

        presence = max(
            scores.get("footsteps", 0.0) * 0.20,
            scores.get("speaking", 0.0) * 0.06,
            scores.get("whispering", 0.0) * 0.03,
            scores.get("crowd_murmur", 0.0) * 0.05,
        )

        if dominant_sound_type in {"whispering", "speaking", "crowd_murmur"}:
            return float(np.clip(max(presence, danger * 0.20), 0.0, 1.0))

        if dominant_sound_type in {"footsteps"}:
            return float(np.clip(max(presence, danger * 0.50), 0.0, 1.0))

        return float(np.clip(max(danger, presence), 0.0, 1.0))

    def _build_description(self, sorted_scores):
        top = [(k, v) for k, v in sorted_scores[:4] if v >= 0.10]
        if not top:
            return "dominant sound: silence"

        dominant = top[0][0]
        others = ", ".join([f"{k}({v:.2f})" for k, v in top[1:]])
        if others:
            return f"dominant sound: {dominant}; secondary: {others}"
        return f"dominant sound: {dominant}"

    # ----------------------------------------------------------
    # Public API
    # ----------------------------------------------------------
    def submit(self, audio_waveform):
        audio_waveform = self._sanitize_audio(audio_waveform)
        if audio_waveform is None:
            self._result = []
            return

        profile = self._audio_profile(audio_waveform)
        heuristic_scores = self._heuristic_scores(profile)

        try:
            clap_scores = self._clap_scores(audio_waveform)
        except Exception:
            clap_scores = {}

        scores = self._combine_scores(clap_scores, heuristic_scores)

        dominant_sound_type = max(scores, key=scores.get) if scores else "silence"
        dominant_sound_confidence = float(scores.get(dominant_sound_type, 0.0))

        sorted_scores = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)

        audio_events = [
            {"sound_type": k, "confidence": float(v)}
            for k, v in sorted_scores
            if v >= 0.20 and k != "silence"
        ]

        threat_score = self._threat_from_sound_scores(scores, profile, dominant_sound_type)
        audio_description = self._build_description(sorted_scores)

        self._result = [{
            "kind": "audio_scene",
            "sound_type_scores": scores,
            "dominant_sound_type": dominant_sound_type,
            "dominant_sound_confidence": dominant_sound_confidence,
            "audio_events": audio_events,
            "audio_profile": profile,
            "audio_description": audio_description,
            "threat_score": threat_score,
            "confidence": threat_score,
            # legacy / compatibility
            "metallic": float(scores.get("metal_clash", 0.0)),
            "shout": float(scores.get("shouting", 0.0)),
            "speech": float(max(scores.get("speaking", 0.0), scores.get("whispering", 0.0), scores.get("crowd_murmur", 0.0))),
            "footsteps": float(scores.get("footsteps", 0.0)),
            "summary": audio_description,
        }]

    def poll(self):
        return self._result