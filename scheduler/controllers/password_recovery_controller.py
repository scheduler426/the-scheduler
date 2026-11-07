"""Handles "forgot password" and "set a new password".

Neither handler needs a session. Forgot-password always gives the same
answer so a caller cannot tell which emails have accounts. The controller
does not read the reset token; PasswordRecoveryService checks it.
"""

from __future__ import annotations

from scheduler.controllers.response import Response, respond
from scheduler.services.password_recovery_service import PasswordRecoveryService


class PasswordRecoveryController:
    """Turns password-recovery requests into PasswordRecoveryService calls and Responses."""
    RESET_SENT_MESSAGE = "If an account exists for that email, a reset link has been sent."

    def __init__(self, recoveryService: PasswordRecoveryService):
        self._recoveryService = recoveryService

    def handleForgotPassword(self, request: dict) -> Response:
        if "email" not in request:
            return Response(Response.INVALID, message="Email is required")
        self._recoveryService.requestResetLink(request["email"])
        return Response(Response.OK, message=self.RESET_SENT_MESSAGE)

    def handleResetPassword(self, request: dict) -> Response:
        return respond(lambda: self._recoveryService.completePasswordReset(
            request.get("token"), request.get("newPassword")
        ))
