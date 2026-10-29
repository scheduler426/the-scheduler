from __future__ import annotations

from scheduler.domain.user import User
from scheduler.infrastructure.password_hasher import PasswordHasher
from scheduler.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, userRepo: UserRepository, hasher: PasswordHasher):
        self._userRepo = userRepo
        self._hasher = hasher

    def registerUser(self, email: str, password: str, firstName: str, lastName: str) -> User:
        email = self._normalizeEmail(email)
        if not firstName.strip() or not lastName.strip():
            raise ValueError("First and last name are required")
        if self._userRepo.findByEmail(email) is not None:
            raise ValueError("An account with this email already exists")
        userId = self._userRepo.save(User(None, email, self._hasher.hash(password), firstName.strip(), lastName.strip()))
        return self._requireUser(userId)

    def updateProfileData(self, userId: int, email: str, firstName: str, lastName: str) -> None:
        user = self._requireUser(userId)
        email = self._normalizeEmail(email)
        owner = self._userRepo.findByEmail(email)
        if owner is not None and owner.userId != userId:
            raise ValueError("Email is already in use by another account")
        self._userRepo.save(
            User(userId, email, user.passwordHash, firstName.strip(), lastName.strip(), user.allowEmailReminders)
        )

    def deleteUserAccount(self, userId: int, password: str) -> None:
        user = self._requireUser(userId)
        if not self._hasher.verify(password, user.passwordHash):
            raise PermissionError("Password is incorrect")
        self._userRepo.delete(userId)

    def _requireUser(self, userId: int) -> User:
        user = self._userRepo.findById(userId)
        if user is None:
            raise LookupError("User not found")
        return user

    @staticmethod
    def _normalizeEmail(email: str) -> str:
        email = (email or "").strip().lower()
        local, _, domain = email.partition("@")
        if not local or "." not in domain:
            raise ValueError("A valid email address is required")
        return email
