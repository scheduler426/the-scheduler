from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Optional


class TokenProvider:
    def __init__(self, secretKey: str, tokenValidityInMs: int = 3_600_000):
        if not secretKey:
            raise ValueError("secretKey is required")
        self._secretKey = secretKey.encode("utf-8")
        self._tokenValidityInMs = tokenValidityInMs

    def generateToken(self, payload: str) -> str:
        claims = {"payload": payload, "exp": self._nowMs() + self._tokenValidityInMs}
        body = self._encode(json.dumps(claims, separators=(",", ":")).encode("utf-8"))
        return f"{body}.{self._sign(body)}"

    def validateToken(self, token: str) -> bool:
        return self._claimsOf(token) is not None

    def getPayload(self, token: str) -> str:
        claims = self._claimsOf(token)
        if claims is None:
            raise ValueError("Invalid or expired token")
        return claims["payload"]

    def _claimsOf(self, token: str) -> Optional[dict]:
        try:
            body, signature = token.split(".")
            if not hmac.compare_digest(signature, self._sign(body)):
                return None
            claims = json.loads(self._decode(body))
        except (ValueError, AttributeError):
            return None
        if claims.get("exp", 0) <= self._nowMs():
            return None
        return claims

    def _sign(self, body: str) -> str:
        return self._encode(hmac.new(self._secretKey, body.encode("utf-8"), hashlib.sha256).digest())

    @staticmethod
    def _encode(raw: bytes) -> str:
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

    @staticmethod
    def _decode(text: str) -> bytes:
        return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))

    @staticmethod
    def _nowMs() -> int:
        return int(time.time() * 1000)
