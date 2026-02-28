from vision.core.intent.states import PersonIntent, GroupIntent, SceneIntent


class ThreatScorer:
    def score(self, person_intents, group_intent, weapon_states, global_hint=None):
        """
        Returns threat level 1–5 based on actor intent and weapon evidence.
        Fuses per-track precision (weapon_states) with scene recall (global_hint).
        """

        # --- SIGNAL 1: LOCAL PRECISION (Per-Track) ---
        has_confirmed_weapon = any(ws and ws.get("confirmed") for ws in weapon_states)
        has_suspicious_weapon = any(ws and ws.get("weapon") not in ["none", "unknown", None] for ws in weapon_states)

        # --- SIGNAL 2: GLOBAL RECALL (Full-Frame VLM) ---
        # If the global scene check sees a weapon, but crops are unclear, we flag it.
        global_weapon_alert = False
        if global_hint and isinstance(global_hint, dict):
            if global_hint.get("weapon_present") is True:
                global_weapon_alert = True

        # --- INTENT & COORDINATION CHECKS ---
        hostile = any(p in [PersonIntent.AGGRESSIVE, PersonIntent.ATTACKING] for p in person_intents)
        coordinated = group_intent in [GroupIntent.COORDINATED, GroupIntent.SURROUNDING]

        # 1. BASELINE SAFETY (Low Threat)
        # No confirmed weapon + no global alert + no hostile/coordinated behavior
        if not has_confirmed_weapon and not global_weapon_alert and not hostile and not coordinated:
            return 1 if all(p == PersonIntent.IDLE for p in person_intents) else 2

        # 2. ESCALATION LADDER (Fusion Logic)

        # Level 5: Extreme Threat (Confirmed weapon + Active attack)
        if has_confirmed_weapon and any(p == PersonIntent.ATTACKING for p in person_intents):
            return 5

        # Level 4: High Threat (Confirmed weapon OR Local + Global agreement on suspicious items)
        if has_confirmed_weapon and hostile:
            return 4
        if has_suspicious_weapon and global_weapon_alert:
            return 4  # High confidence due to dual-signal agreement

        # Level 3: Elevated Threat (Suspicious weapon, Global alert, or Coordinated group)
        if has_suspicious_weapon or global_weapon_alert or coordinated or hostile:
            return 3

        return 2