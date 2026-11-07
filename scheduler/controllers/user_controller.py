"""Handles sign-up, profile updates, password changes, and account deletion.

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

    def handleChangePassword(self, request: dict) -> Response:
        return respond(lambda: self._changePassword(request))

    def handleDeleteAccount(self, request: dict) -> Response:
        return respond(lambda: self._deleteAccount(request))

    def _changePassword(self, request: dict) -> None:
        session = self._authService.requireSession(request.get("token"))
        currentPassword, newPassword = self._required(request, "currentPassword", "newPassword")
        self._userService.changePassword(session.userId, currentPassword, newPassword)

    def _updateProfile(self, request: dict) -> None:
        session = self._authService.requireSession(request.get("token"))
        email, firstName, lastName = self._required(request, "email", "firstName", "lastName")
        self._userService.updateProfileData(session.userId, email, firstName, lastName)

    def _deleteAccount(self, request: dict) -> None:
        session = self._authService.requireSession(request.get("token"))
        (password,) = self._required(request, "password")
        self._userService.deleteUserAccount(session.userId, password)
        self._sessionManager.removeSessionsForUser(session.userId)

    @staticmethod
    def _required(request: dict, *keys: str) -> list:
        """Return the values for keys, raising ValueError for the first one that is missing."""
        for key in keys:
            if request.get(key) is None:
                raise ValueError(f"{key} is required")
        return [request[key] for key in keys]

    @staticmethod
    def _publicUser(user: User) -> dict:
        return {
            "userId": user.userId,
            "email": user.email,
            "firstName": user.firstName,
            "lastName": user.lastName,
            "allowEmailReminders": user.allowEmailReminders,
        }
