import base64
import os
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Put your base64 key here
AES_KEY_B64 = "80iM3AV86Lz2/9GI5J9dBiBRCE3jVZ+hveXdJw6JTeU="
KEY = base64.b64decode(AES_KEY_B64)

def encrypt_json(json_bytes: bytes) -> dict:
    aesgcm = AESGCM(KEY)
    iv = os.urandom(12)  # 96-bit nonce for GCM
    ciphertext = aesgcm.encrypt(iv, json_bytes, None)

    return {
        "iv": base64.b64encode(iv).decode(),
        "ciphertext": base64.b64encode(ciphertext).decode()
    }