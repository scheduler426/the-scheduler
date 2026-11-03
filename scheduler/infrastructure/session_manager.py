"""Tracks who is logged in for this process only.

Sessions are plain dicts in memory. There is no UserSession class and no
session table. TokenProvider signs the token that keys each dict.
AuthenticationService creates a session at login and removes it at logout.
A new process starts with an empty map.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Optional

from scheduler.infrastructure.token_provider import TokenProvider


class SessionManager:
    """In-memory map of token to session fields.

    Each dict holds the session id, user id, token, login time, and expiry.
    The default lifetime is eight hours, and the signed token must still
    validate. This class does not load a User.
    """
    def __init__(self, tokenProvider: TokenProvider, sessionDuration: timedelta = timedelta(hours=8)):
        self._tokenProvider = tokenProvider
        self._sessionDuration = sessionDuration
        self._activeSessions: dict[str, dict] = {}

    def createSession(self, userId: int) -> dict:
        """Sign a token for userId, store the session, and return a copy."""
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
        """Return a copy of an active session, or None."""
        if not self.isSessionActive(token):
            return None
        return dict(self._activeSessions[token])

    def isSessionActive(self, token: str) -> bool:
        """True when the session exists, has not expired, and the token still validates.

        A failed check removes the stored session.
        """
        session = self._activeSessions.get(token)
        if session is None:
            return False
        if datetime.now() >= session["expiryTime"] or not self._tokenProvider.validateToken(token):
            self.removeSession(token)
            return False
        return True

    def extendSession(self, token: str, duration: int) -> None:
        """Add duration seconds to an active session's expiry."""
        if not self.isSessionActive(token):
            raise LookupError("Session is not active")
        self._activeSessions[token]["expiryTime"] += timedelta(seconds=duration)

    def removeSession(self, token: str) -> None:
        """Forget the session. A missing token is ignored."""
        self._activeSessions.pop(token, None)
