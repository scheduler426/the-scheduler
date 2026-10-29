from __future__ import annotations

from scheduler.infrastructure.password_hasher import PasswordHasher
from scheduler.infrastructure.session_manager import SessionManager
from scheduler.repositories.user_repository import UserRepository


class AuthenticationService:
    def __init__(self, userRepo: UserRepository, sessionManager: SessionManager, hasher: PasswordHasher):
        self._userRepo = userRepo
        self._sessionManager = sessionManager
        self._hasher = hasher

    def login(self, email: str, password: str) -> dict:
        user = self._userRepo.findByEmail((email or "").strip())
        if user is None or not self._hasher.verify(password, user.passwordHash):
            raise PermissionError("Invalid email or password")
        return self._sessionManager.createSession(user.userId)

    def logout(self, token: str) -> None:
        self._sessionManager.removeSession(token)

    def validateToken(self, token: str) -> bool:
        return self._sessionManager.isSessionActive(token)
