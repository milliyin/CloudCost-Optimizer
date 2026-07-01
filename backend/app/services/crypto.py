from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import settings


def _resolved_key() -> bytes:
    if settings.aws_connection_encryption_key:
        return settings.aws_connection_encryption_key.encode("utf-8")

    digest = hashlib.sha256(settings.jwt_secret_key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest)


fernet = Fernet(_resolved_key())


def encrypt_secret(value: str) -> str:
    return fernet.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value: str) -> str:
    return fernet.decrypt(value.encode("utf-8")).decode("utf-8")
