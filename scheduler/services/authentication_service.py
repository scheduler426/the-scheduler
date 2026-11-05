"""Logs an existing user in and out.

UserRepository finds the account. PasswordHasher checks the password;
login uses that hasher even though the class diagram omits the arrow.
SessionManager keeps the session in memory, and logout drops it. This
service does not register users or issue a password-reset token.
"""

from __future__ import annotations

from scheduler.domain.user_session import UserSession
from scheduler.infrastructure.password_hasher import PasswordHasher
from scheduler.infrastructure.session_manager import SessionManager
from scheduler.repositories.user_repository import UserRepository


class AuthenticationService:
    """Login, logout, and a check that a session token is still active.

    login returns the UserSession from SessionManager. A missing account
    and a wrong password raise the same error. validateToken asks
    SessionManager and does not decode the token itself.
    """
    def __init__(self, userRepo: UserRepository, sessionManager: SessionManager, hasher: PasswordHasher):
        self._userRepo = userRepo
        self._sessionManager = sessionManager
        self._hasher = hasher

    def login(self, email: str, password: str) -> UserSession:
        """Return a new session when the email and password match."""
        user = self._userRepo.findByEmail((email or "").strip())
        if user is None or not self._hasher.verify(password, user.passwordHash):
            raise PermissionError("Invalid email or password")
        return self._sessionManager.createSession(user.userId)

    def logout(self, token: str) -> None:
        """Remove the session for this token."""
        self._sessionManager.removeSession(token)

    def validateToken(self, token: str) -> bool:
        """True when SessionManager still treats the token as an active session."""
        return self._sessionManager.isSessionActive(token)
