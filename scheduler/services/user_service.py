"""Creates an account, updates its profile, and deletes it.

UserRepository stores the user. PasswordHasher hashes the password on
register and checks it before delete. deleteUserAccount then asks the
repository to delete; roster, availability, and vote cleanup is in
UserRepository.delete. This service does not log the user in or send mail.
"""

from __future__ import annotations

from scheduler.domain.user import User
from scheduler.infrastructure.password_hasher import PasswordHasher
from scheduler.repositories.user_repository import UserRepository


class UserService:
    """Registration, profile edits, and account deletion.

    Email is stored in lower case, and a duplicate email is rejected.
    A profile update changes the email and name and keeps the current
    password hash and reminder flag.
    """
    def __init__(self, userRepo: UserRepository, hasher: PasswordHasher):
        self._userRepo = userRepo
        self._hasher = hasher

    def registerUser(self, email: str, password: str, firstName: str, lastName: str) -> User:
        """Store a new user and return the saved row. The password is stored as a hash."""
        email = self._normalizeEmail(email)
        if not firstName.strip() or not lastName.strip():
            raise ValueError("First and last name are required")
        if self._userRepo.findByEmail(email) is not None:
            raise ValueError("An account with this email already exists")
        userId = self._userRepo.save(User(None, email, self._hasher.hash(password), firstName.strip(), lastName.strip()))
        return self._requireUser(userId)

    def updateProfileData(self, userId: int, email: str, firstName: str, lastName: str) -> None:
        """Change the user's email and name. Raises when that email belongs to someone else."""
        user = self._requireUser(userId)
        email = self._normalizeEmail(email)
        owner = self._userRepo.findByEmail(email)
        if owner is not None and owner.userId != userId:
            raise ValueError("Email is already in use by another account")
        self._userRepo.save(
            User(userId, email, user.passwordHash, firstName.strip(), lastName.strip(), user.allowEmailReminders)
        )

    def deleteUserAccount(self, userId: int, password: str) -> None:
        """Delete the account after the password matches. Open sessions are left in place."""
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
