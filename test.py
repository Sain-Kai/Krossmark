import json
import requests
from encryption.crypto_utils import encrypt_json  # if you are using AES-GCM

url = "http://localhost:8080/api/inference/result"

data = {
    "person_count": 3,
    "groups": 1,
    "group_intent": "coordinated_scouting",
    "actors": [
        {"id": 1, "intent": "observing", "weapon": "none"},
        {"id": 2, "intent": "scouting", "weapon": "possible_knife"},
        {"id": 3, "intent": "loitering", "weapon": "none"}
    ],
    "scene_intent": "preparation_phase",
    "threat_level": 3,
    "confidence": 0.81
}

# If you are using encryption:
json_bytes = json.dumps(data).encode("utf-8")
encrypted_payload = encrypt_json(json_bytes)

# 🔐 Spring Security credentials (from your log)
USERNAME = "user"
PASSWORD = "491d886f-fba9-4227-b5ad-bdc1c7424eb4"

r = requests.post(
    url,
    json=encrypted_payload,   # or `json=data` if you temporarily skip encryption
    auth=(USERNAME, PASSWORD),
    timeout=5
)

print("Status:", r.status_code)
print("Response:", r.text)