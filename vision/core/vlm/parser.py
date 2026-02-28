import json


def normalize_weapon(w):
    """
    Collapses various VLM descriptions into a standard semantic vocabulary.
    This prevents the ThreatScorer from missing synonyms.
    """
    if not w or not isinstance(w, str):
        return "none"

    w = w.lower().strip()

    # Semantic mapping for knives/blades
    if w in ["blade", "dagger", "cutter", "pocket knife", "shiv", "machete"]:
        return "knife"

    # Semantic mapping for firearms
    if w in ["pistol", "revolver", "handgun", "glock", "arm"]:
        return "firearm"

    # Semantic mapping for rifles/long guns
    if w in ["rifle", "shotgun", "carbine", "long gun"]:
        return "long_gun"

    return w


def parse_vlm_json(text):
    """
    Extracts JSON from VLM raw output and normalizes weapon descriptions.
    """
    try:
        # 1. Extract first JSON object if extra conversational text sneaks in
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1:
            return None

        raw_json = text[start:end + 1]
        obj = json.loads(raw_json)

        # 2. Apply Semantic Normalization
        # We look for common keys like 'weapon' or 'object_in_hand'
        if "weapon" in obj:
            obj["weapon"] = normalize_weapon(obj["weapon"])
        elif "object_in_hand" in obj:
            # Standardize the key name as well for the rest of the pipeline
            obj["weapon"] = normalize_weapon(obj["object_in_hand"])

        return obj

    except Exception as e:
        # Log error if needed for debugging
        # print(f"[Parser] Failed to parse JSON: {e}")
        return None