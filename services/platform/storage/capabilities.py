"""Short-lived service capabilities shared by storage providers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Callable

from .models import ExpiredPrivateAccessToken, InvalidPrivateAccessToken
from .keys import validate_storage_key

_TOKEN_VERSION = "v1"


class CapabilitySigner:
    """Issue and verify provider-independent, expiring read capabilities."""

    def __init__(
        self,
        signing_secret: str | bytes | None = None,
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if isinstance(signing_secret, str):
            signing_secret = signing_secret.encode("utf-8")
        self._signing_secret = signing_secret or secrets.token_bytes(32)
        self._clock = clock

    def issue(self, key: str, expires_at_epoch: float) -> str:
        payload = self._encode({"key": key, "exp": expires_at_epoch})
        return f"{_TOKEN_VERSION}.{payload}.{self._sign(payload)}"

    def verify(self, token: str) -> dict[str, object]:
        try:
            version, encoded_payload, signature = token.split(".", 2)
            if version != _TOKEN_VERSION:
                raise ValueError
            if not hmac.compare_digest(signature, self._sign(encoded_payload)):
                raise ValueError
            payload = json.loads(self._decode(encoded_payload))
            key = payload["key"]
            expires = payload["exp"]
            if (
                not isinstance(key, str)
                or not isinstance(expires, (int, float))
                or isinstance(expires, bool)
            ):
                raise ValueError
            validate_storage_key(key)
        except (AttributeError, KeyError, TypeError, ValueError, json.JSONDecodeError):
            raise InvalidPrivateAccessToken("Private access token is invalid.") from None

        if self._clock() >= float(expires):
            raise ExpiredPrivateAccessToken("Private access has expired.")
        return {"key": key, "exp": expires}

    def _encode(self, payload: dict[str, object]) -> str:
        encoded = json.dumps(
            payload,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return self._base64url(encoded)

    def _sign(self, payload: str) -> str:
        digest = hmac.new(
            self._signing_secret,
            payload.encode("ascii"),
            hashlib.sha256,
        ).digest()
        return self._base64url(digest)

    @staticmethod
    def _base64url(value: bytes) -> str:
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")

    @staticmethod
    def _decode(value: str) -> bytes:
        padding = "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode(value + padding)