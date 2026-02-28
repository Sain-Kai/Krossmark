class ThreatEngine:
    def compute(self, fused, previous_requests=0):
        # Aggregate evidence across frames
        weapon_votes = 0
        aggressive_votes = 0
        total = 0

        for e in fused["frames"]:
            total += 1
            feats = e["pose_feats"]
            if feats.get("aggressive_pose"):
                aggressive_votes += 1
            vlm = e.get("vlm")
            if vlm and vlm.get("weapon") not in ["none", "unknown"]:
                weapon_votes += 1

        audio = fused["audio"]
        metallic = max([a.get("metallic", 0) for a in audio], default=0)
        shout = max([a.get("shout", 0) for a in audio], default=0)

        # Scores
        weapon_strength = weapon_votes / max(1, total)
        aggression_strength = aggressive_votes / max(1, total)

        # Threat level
        threat = 1
        if aggression_strength > 0.3:
            threat = 2
        if weapon_strength > 0.3 or shout > 0.6:
            threat = 3
        if weapon_strength > 0.5 or metallic > 0.6:
            threat = 4
        if weapon_strength > 0.5 and (metallic > 0.6 or shout > 0.6):
            threat = 5

        # Confidence
        confidence = min(1.0, 0.3 + 0.4*weapon_strength + 0.3*aggression_strength + 0.2*max(metallic, shout))

        # Decision
        if threat >= 4 and confidence >= 0.7:
            decision = "CONFIRM_THREAT"
        elif confidence < 0.5:
            if previous_requests == 0:
                decision = "REQUEST_MORE_DATA"
            else:
                decision = "DISMISS_FALSE_TRIGGER"
        else:
            decision = "REQUEST_MORE_DATA"

        return {
            "decision": decision,
            "threat_level": threat,
            "confidence": round(confidence, 2)
        }