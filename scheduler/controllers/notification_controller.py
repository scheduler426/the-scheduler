# Entry point for sending a manual email reminder to chosen group members.

from __future__ import annotations

from datetime import datetime

from scheduler.controllers.response import Response, respond
from scheduler.services.authentication_service import AuthenticationService
from scheduler.services.group_notification_service import GroupNotificationService


class NotificationController:
    def __init__(self, notificationService: GroupNotificationService, authService: AuthenticationService):
        self._notificationService = notificationService
        self._authService = authService

    # Return the values for keys, raising ValueError for the first one that is missing
    @staticmethod
    def _required(request: dict, *keys: str) -> list:
        for key in keys:
            if request.get(key) is None:
                raise ValueError(f"{key} is required")
        return [request[key] for key in keys]

    # Email a reminder to the chosen members. ok even if every target was skipped.
    def handleSendManualReminder(self, request: dict) -> Response:
        return respond(lambda: self._sendManualReminder(request))

    def _sendManualReminder(self, request: dict) -> None:
        session = self._authService.requireSession(request.get("token"))
        groupId, targetUserIds, message = self._required(request, "groupId", "targetUserIds", "message")
        if not isinstance(targetUserIds, list):
            raise ValueError("targetUserIds must be a list")
        self._notificationService.dispatchManualReminder(groupId, targetUserIds, message, session.userId)
    # Set a reminder for one of the signed-in user's meetings
    def handleSetMeetingReminder(self, request: dict) -> Response:
        return respond(lambda: self._setMeetingReminder(request))

    def _setMeetingReminder(self, request: dict) -> dict:
        session = self._authService.requireSession(request.get("token"))
        meetingId, sendAt = self._required(request, "meetingId", "sendAt")
        if not isinstance(sendAt, datetime):
            raise ValueError("sendAt must be a datetime")
        # Comparing a timezone-aware time with datetime.now() would raise TypeError
        if sendAt.tzinfo is not None:
            raise ValueError("sendAt must not have a timezone")
        notificationId = self._notificationService.scheduleMeetingReminder(session.userId, meetingId, sendAt)
        return {"notificationId": notificationId, "meetingId": meetingId, "sendAt": sendAt}