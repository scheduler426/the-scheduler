"""Emails a one-time password-reset token and sets a new password with it.

TokenProvider signs the token with the payload reset:<userId>; the token is
not stored anywhere and stops working when it expires. EmailService sends it
using the text from AuthEmailTemplateFactory. requestResetLink behaves the
same whether or not the email has an account. A reset does not log the user in.
"""

from __future__ import annotations

from scheduler.domain.user import User
from scheduler.infrastructure.auth_email_template_factory import AuthEmailTemplateFactory
from scheduler.infrastructure.email_service import EmailService, MailDeliveryError
from scheduler.infrastructure.password_hasher import PasswordHasher
from scheduler.infrastructure.token_provider import TokenProvider
from scheduler.repositories.user_repository import UserRepository


class PasswordRecoveryService:
    """Request a reset token by email, then complete the reset with it."""
    _PAYLOAD_PREFIX = "reset:"

    def __init__(
        self,
        userRepo: UserRepository,
        tokenProvider: TokenProvider,
        emailService: EmailService,
        templateFactory: AuthEmailTemplateFactory,
        hasher: PasswordHasher,
    ):
        self._userRepo = userRepo
        self._tokenProvider = tokenProvider
        self._emailService = emailService
        self._templateFactory = templateFactory
        self._hasher = hasher

    def requestResetLink(self, email: str) -> None:
        """Email a reset token when the address has an account. Never raises for an unknown or bad address."""
        email = (email or "").strip().lower()
        local, _, domain = email.partition("@")
        if not local or "." not in domain:
            return
        user = self._userRepo.findByEmail(email)
        if user is None:
            return
        token = self._tokenProvider.generateToken(f"{self._PAYLOAD_PREFIX}{user.userId}")
        try:
            self._emailService.sendEmail(
                user.email, "Reset your scheduler password", self._templateFactory.buildResetEmail(token)
            )
        except MailDeliveryError:
            return

    def completePasswordReset(self, token: str, newPassword: str) -> None:
        """Replace the user's password hash when the reset token is valid."""
        user = self._requireUser(self._userIdFromToken(token))
        if (
            len(newPassword or "") < 8
            or not any(c.isalpha() for c in newPassword)
            or not any(c.isdigit() for c in newPassword)
        ):
            raise ValueError("Password must be at least 8 characters and include a letter and a digit")
        self._userRepo.save(
            User(
                user.userId,
                user.email,
                self._hasher.hash(newPassword),
                user.firstName,
                user.lastName,
                user.allowEmailReminders,
            )
        )

    def _userIdFromToken(self, token: str) -> int:
        try:
            payload = self._tokenProvider.getPayload(token)
            if not payload.startswith(self._PAYLOAD_PREFIX):
                raise ValueError
            return int(payload.removeprefix(self._PAYLOAD_PREFIX))
        except (ValueError, TypeError, AttributeError):
            raise ValueError("Invalid or expired token") from None

    def _requireUser(self, userId: int) -> User:
        user = self._userRepo.findById(userId)
        if user is None:
            raise LookupError("User not found")
        return user
