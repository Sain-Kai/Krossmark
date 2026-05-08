import time

class OutputPacker:
    def compute_confidence(self, actors, group_intent, scene_intent, threat_level):
        score = 0.3  # base

        # Weapon evidence boosts confidence
        for a in actors:
            ws = a.get("weapon_state")
            if ws and ws.get("confirmed"):
                score += 0.3
            elif ws and ws.get("weapon") not in ["none", "unknown", None]:
                score += 0.15

        # Higher threat & severe scene boosts confidence
        if threat_level >= 4:
            score += 0.2
        elif threat_level == 3:
            score += 0.1

        if str(scene_intent).endswith("ATTACK"):
            score += 0.2
        elif str(scene_intent).endswith("PREPARATION"):
            score += 0.1

        return max(0.0, min(1.0, round(score, 2)))

    def pack(self, actors, group_intent, scene_intent, threat_level, explanations):
        return {
            "timestamp": time.time(),
            "person_count": len(actors),
            "groups": 0 if group_intent is None else 1,  # you can refine with real group count
            "group_intent": str(group_intent),
            "scene_intent": str(scene_intent),
            "threat_level": int(threat_level),
            "actors": [
                {
                    "id": a["id"],
                    "intent": str(a.get("intent")),
                    "weapon": (a.get("weapon_state") or {}).get("weapon", "none"),
                    "weapon_confirmed": (a.get("weapon_state") or {}).get("confirmed", False)
                }
                for a in actors
            ],
            "confidence": self.compute_confidence(actors, group_intent, scene_intent, threat_level),
            "explanations": explanations
        }