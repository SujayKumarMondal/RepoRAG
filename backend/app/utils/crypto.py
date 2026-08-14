"""
Simple token encryption utilities using Fernet symmetric encryption.
The Fernet key is derived from `settings.SECRET_KEY` by SHA256 + base64url encoding.

Functions:
- encrypt_token(plaintext: str) -> str
- decrypt_token(token: str) -> str

Note: In production you should use a dedicated KMS or secrets manager.
"""
from __future__ import annotations

import base64
import hashlib
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _derive_fernet_key() -> bytes:
    secret = settings.SECRET_KEY or ""
    # Ensure secret is long enough; derive 32-byte key via SHA256, then base64-url encode
    digest = hashlib.sha256(secret.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_token(plaintext: str) -> str:
    key = _derive_fernet_key()
    f = Fernet(key)
    token = f.encrypt(plaintext.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_token(token: str) -> Optional[str]:
    if not token:
        return None
    key = _derive_fernet_key()
    f = Fernet(key)
    try:
        plain = f.decrypt(token.encode("utf-8"))
        return plain.decode("utf-8")
    except InvalidToken:
        return None
