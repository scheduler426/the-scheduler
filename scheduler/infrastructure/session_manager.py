from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Optional

from scheduler.infrastructure.token_provider import TokenProvider


class SessionManager:
    def __init__(self, tokenProvider: TokenProvider, sessionDuration: timedelta = timedelta(hours=8)):
        self._tokenProvider = tokenProvider
        self._sessionDuration = sessionDuration
        self._activeSessions: dict[str, dict] = {}

    def createSession(self, userId: int) -> dict:
        now = datetime.now()
        token = self._tokenProvider.generateToken(str(userId))
        self._activeSessions[token] = {
            "userSessionId": str(uuid.uuid4()),
            "userId": userId,
            "token": token,
            "loginTime": now,
            "expiryTime": now + self._sessionDuration,
        }
        return dict(self._activeSessions[token])

    def getSession(self, token: str) -> Optional[dict]:
        if not self.isSessionActive(token):
            return None
        return dict(self._activeSessions[token])

    def isSessionActive(self, token: str) -> bool:
        session = self._activeSessions.get(token)
        if session is None:
            return False
        if datetime.now() >= session["expiryTime"] or not self._tokenProvider.validateToken(token):
            self.removeSession(token)
            return False
        return True

    def extendSession(self, token: str, duration: int) -> None:
        if not self.isSessionActive(token):
            raise LookupError("Session is not active")
        self._activeSessions[token]["expiryTime"] += timedelta(seconds=duration)

    def removeSession(self, token: str) -> None:
        self._activeSessions.pop(token, None)
