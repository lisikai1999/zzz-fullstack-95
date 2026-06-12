import os
import base64
from hashlib import sha256

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _derive_key(secret_key: str) -> bytes:
    return sha256(secret_key.encode()).digest()


def encrypt_value(plaintext: str, secret_key: str) -> str:
    key = _derive_key(secret_key)
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return base64.b64encode(nonce + ciphertext).decode()


def decrypt_value(encrypted: str, secret_key: str) -> str:
    key = _derive_key(secret_key)
    raw = base64.b64decode(encrypted)
    nonce, ciphertext = raw[:12], raw[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None).decode()
