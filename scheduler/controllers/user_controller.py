"""Handles sign-up, profile updates, and account deletion.

Registration needs no session; the other handlers require one. UserService
applies every rule, including the password check before deletion. After a
deletion, every session for that user is removed. Responses carry the
public user fields and never the password hash.
"""

from __future__ import annotations

from scheduler.controllers.response import Response, respond
from scheduler.domain.user import User
from scheduler.infrastructure.session_manager import SessionManager
from scheduler.services.authentication_service import AuthenticationService
from scheduler.services.user_service import UserService


class UserController:
    """Turns account requests into UserService calls and Responses."""
    def __init__(self, userService: UserService, authService: AuthenticationService, sessionManager: SessionManager):
        self._userService = userService
        self._authService = authService
        self._sessionManager = sessionManager

    def handleRegisterUser(self, request: dict) -> Response:
        return respond(lambda: self._publicUser(
            self._userService.registerUser(
                request.get("email"), request.get("password"), request.get("firstName", ""), request.get("lastName", "")
            )
        ))

    def handleUpdateProfile(self, request: dict) -> Response:
        return respond(lambda: self._updateProfile(request))

    def handleDeleteAccount(self, request: dict) -> Response:
        return respond(lambda: self._deleteAccount(request))

    def _updateProfile(self, request: dict) -> None:
        session = self._authService.requireSession(request.get("token"))
        self._userService.updateProfileData(session.userId, request["email"], request["firstName"], request["lastName"])

    def _deleteAccount(self, request: dict) -> None:
        session = self._authService.requireSession(request.get("token"))
        self._userService.deleteUserAccount(session.userId, request["password"])
        self._sessionManager.removeSessionsForUser(session.userId)

    @staticmethod
    def _publicUser(user: User) -> dict:
        return {
            "userId": user.userId,
            "email": user.email,
            "firstName": user.firstName,
            "lastName": user.lastName,
            "allowEmailReminders": user.allowEmailReminders,
        }
