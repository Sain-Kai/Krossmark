FULL_FRAME_PROMPT = """You are a security analysis AI.
Look at the FULL IMAGE and answer ONLY in valid JSON:

{
  "weapon_present": true|false,
  "weapon_type": "none|knife|gun|tool|stick|unknown",
  "confidence": 0.0-1.0
}

Rules:
- Scan the entire image.
- If any blade/knife/sharp object is visible anywhere, set weapon_present=true.
- Do not add text outside JSON.
"""

HAND_CROP_PROMPT = """You are a security analysis AI.
Look at the HAND / TORSO CROP and answer ONLY in valid JSON:

{
  "weapon": "none|knife|gun|tool|stick|unknown",
  "weapon_confidence": 0.0-1.0
}

Rules:
- Focus on objects being held in hands.
- If a blade or knife is visible, set weapon="knife".
- Do not add text outside JSON.
"""