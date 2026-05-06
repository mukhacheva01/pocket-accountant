from __future__ import annotations

import logging
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken


logger = logging.getLogger(__name__)


class SecretBox:
    PREFIX = "enc-v1:"

    def __init__(self, secret_key: str = "", *, allow_insecure_fallback: bool = True) -> None:
        self._secret_key = (secret_key or "").strip()
        self._allow_insecure_fallback = allow_insecure_fallback
        self._fernet: Optional[Fernet] = None
        if self._secret_key:
            self._fernet = Fernet(self._secret_key.encode())

    @property
    def enabled(self) -> bool:
        return self._fernet is not None

    @property
    def can_store_plaintext(self) -> bool:
        return self._fernet is None and self._allow_insecure_fallback

    def encrypt(self, value: str) -> str:
        if not value:
            return value
        if value.startswith(self.PREFIX):
            return value
        if self._fernet is None:
            if not self._allow_insecure_fallback:
                raise RuntimeError("APP_SECRET_KEY is required to store marketplace secrets safely")
            logger.warning("secret_box_disabled_encrypt_passthrough")
            return value
        token = self._fernet.encrypt(value.encode("utf-8")).decode("utf-8")
        return f"{self.PREFIX}{token}"

    def decrypt(self, value: str) -> str:
        if not value:
            return value
        if not value.startswith(self.PREFIX):
            return value
        if self._fernet is None:
            raise RuntimeError("APP_SECRET_KEY is required to decrypt stored secrets")
        token = value[len(self.PREFIX) :]
        try:
            return self._fernet.decrypt(token.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise RuntimeError("Stored secret cannot be decrypted with current APP_SECRET_KEY") from exc

    def is_encrypted(self, value: str) -> bool:
        return bool(value and value.startswith(self.PREFIX))
