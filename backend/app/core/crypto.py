"""Encryption of stored secrets (users' AI API keys)."""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import Settings

# Only for local development and tests; production refuses to start without SECRET_KEY.
_DEVELOPMENT_SECRET = "spektrum-local-development-only"


class SecretBox:
    def __init__(self, secret: str) -> None:
        key = base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())
        self._fernet = Fernet(key)

    @classmethod
    def from_settings(cls, settings: Settings) -> "SecretBox":
        if settings.secret_key is not None:
            return cls(settings.secret_key.get_secret_value())
        return cls(_DEVELOPMENT_SECRET)

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("ascii")

    def decrypt(self, token: str) -> str | None:
        """None when the value was encrypted with another secret (e.g. SECRET_KEY changed)."""
        try:
            return self._fernet.decrypt(token.encode("ascii")).decode("utf-8")
        except InvalidToken:
            return None
