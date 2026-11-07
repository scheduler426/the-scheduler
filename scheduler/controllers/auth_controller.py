"""Handles logging in and logging out.

Login needs no session and returns the new session's token, which the
caller sends back as request["token"]. Logout requires an active session.
AuthenticationService checks the password; a wrong email and a wrong
password give the same forbidden response.
"""

from __future__ import annotations

from scheduler.controllers.response import Response, respond
from scheduler.domain.user_session import UserSession
from scheduler.services.authentication_service import AuthenticationService


class AuthController:
    """Turns login and logout requests into AuthenticationService calls and Responses."""
    def __init__(self, authService: AuthenticationService):
        self._authService = authService

    def handleLogin(self, request: dict) -> Response:
        return respond(lambda: self._sessionData(
            self._authService.login(request.get("email"), request.get("password"))
        ))

    def handleLogout(self, request: dict) -> Response:
        return respond(lambda: self._logout(request))

    def _logout(self, request: dict) -> None:
        session = self._authService.requireSession(request.get("token"))
        self._authService.logout(session.token)

    @staticmethod
    def _sessionData(session: UserSession) -> dict:
        return {
            "userSessionId": session.userSessionId,
            "userId": session.userId,
            "token": session.token,
            "loginTime": session.loginTime,
            "expiryTime": session.expiryTime,
        }
