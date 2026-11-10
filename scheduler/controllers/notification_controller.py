# Entry point for sending a manual email reminder to chosen group members.

from __future__ import annotations

from scheduler.controllers.response import Response, respond
from scheduler.services.authentication_service import AuthenticationService
from scheduler.services.group_notification_service import GroupNotificationService


class NotificationController:
    def __init__(self, notificationService: GroupNotificationService, authService: AuthenticationService):
        self._notificationService = notificationService
        self._authService = authService

    # Email a reminder to the chosen members. ok even if every target was skipped.
    def handleSendManualReminder(self, request: dict) -> Response:
        return respond(lambda: self._sendManualReminder(request))

    def _sendManualReminder(self, request: dict) -> None:
        session = self._authService.requireSession(request.get("token"))
        targetUserIds = request.get("targetUserIds")
        if not isinstance(targetUserIds, list):
            raise ValueError("targetUserIds must be a list")
        self._notificationService.dispatchManualReminder(
            request.get("groupId"), targetUserIds, request.get("message"), session.userId
        )