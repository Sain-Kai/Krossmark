from vision.core.intent.states import PersonIntent, GroupIntent, SceneIntent

class Explainer:
    def explain(self, actors, group_intent, scene_intent, threat_level):
        reasons = []

        # Group-based reasons
        if group_intent and str(group_intent).endswith("COORDINATED"):
            reasons.append("Multiple actors moving in coordination")

        # Person-based reasons
        for a in actors:
            intent = a.get("intent")
            ws = a.get("weapon_state")

            if intent == PersonIntent.AGGRESSIVE:
                reasons.append(f"Actor {a['id']} shows aggressive behavior")
            if intent == PersonIntent.ATTACKING:
                reasons.append(f"Actor {a['id']} appears to be attacking")

            if ws and ws.get("confirmed"):
                reasons.append(f"Actor {a['id']} has a confirmed weapon: {ws.get('weapon')}")
            elif ws and ws.get("weapon") not in ["none", "unknown", None]:
                reasons.append(f"Actor {a['id']} may be holding: {ws.get('weapon')}")

        # Scene-based
        if scene_intent == SceneIntent.PREPARATION:
            reasons.append("Scene shows signs of preparation or escalation")
        elif scene_intent == SceneIntent.ATTACK:
            reasons.append("Scene indicates an active attack")

        # Fallback
        if not reasons:
            reasons.append("No significant threat indicators detected")

        # Deduplicate
        return list(dict.fromkeys(reasons))