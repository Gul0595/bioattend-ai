"""
BioAttend Ultimate — Biometric Encryption Service
==================================================
AES-256-GCM encryption for face embeddings at rest.
GDPR Art. 9 & India DPDP Act compliance.

Each embedding is: base64(IV + TAG + CIPHERTEXT)
Key is derived from SECRET_KEY using PBKDF2-HMAC-SHA256.
"""
from __future__ import annotations

import base64
import json
import os
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

_SALT = b"bioattend-face-embedding-salt-v1"   # fixed salt (version-tied)
_KEY_CACHE: Optional[bytes] = None


def _derive_key() -> bytes:
    global _KEY_CACHE
    if _KEY_CACHE is not None:
        return _KEY_CACHE
    from app.core.config import settings
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=_SALT,
        iterations=100_000,
    )
    _KEY_CACHE = kdf.derive(settings.SECRET_KEY.encode())
    return _KEY_CACHE


def encrypt_embedding(embedding: list[float]) -> str:
    """
    Encrypt a list of floats → base64 string safe to store in DB.
    Format: base64( 12-byte-IV || 16-byte-GCM-tag || ciphertext )
    """
    key  = _derive_key()
    aesgcm = AESGCM(key)
    iv   = os.urandom(12)
    data = json.dumps(embedding, separators=(",", ":")).encode()
    ct   = aesgcm.encrypt(iv, data, None)  # ct includes tag appended by cryptography lib
    blob = iv + ct
    return base64.b64encode(blob).decode()


def decrypt_embedding(encrypted: str) -> list[float]:
    """
    Decrypt a base64 string → list[float].
    Raises ValueError on tampered / wrong-key data.
    """
    key    = _derive_key()
    aesgcm = AESGCM(key)
    blob   = base64.b64decode(encrypted)
    iv     = blob[:12]
    ct     = blob[12:]
    data   = aesgcm.decrypt(iv, ct, None)
    return json.loads(data.decode())


def rotate_key_reencrypt(old_secret: str, embeddings_encrypted: list[str]) -> list[str]:
    """
    Utility: re-encrypt all embeddings with new key after SECRET_KEY rotation.
    Run this once after updating SECRET_KEY in production.
    """
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    old_kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=_SALT, iterations=100_000)
    old_key = old_kdf.derive(old_secret.encode())
    old_gcm = AESGCM(old_key)

    new_key = _derive_key()
    new_gcm = AESGCM(new_key)

    result = []
    for enc in embeddings_encrypted:
        blob = base64.b64decode(enc)
        iv, ct = blob[:12], blob[12:]
        data = old_gcm.decrypt(iv, ct, None)
        new_iv = os.urandom(12)
        new_ct = new_gcm.encrypt(new_iv, data, None)
        result.append(base64.b64encode(new_iv + new_ct).decode())
    return result
