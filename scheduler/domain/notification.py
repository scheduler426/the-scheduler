# A reminder a member asked to get about one meeting.
# It stores who gets the reminder, which meeting it is about, the text,
# when to send it, and whether it has been sent.
# NotificationRepository saves it. This class does not send email or touch the database.

from __future__ import annotations

from datetime import datetime
from typing import Optional


class Notification:
    SCHEDULED = "scheduled"
    SENT = "sent"

    def __init__(
        self,
        notificationId: Optional[int],
        groupId: int,
        userId: int,
        meetingId: int,
        message: str,
        sendAt: datetime,
        status: str = SCHEDULED,
    ):
        self._notificationId = notificationId
        self._groupId = groupId
        self._userId = userId
        self._meetingId = meetingId
        self._message = message
        self._sendAt = sendAt
        self._status = status

    @property
    def notificationId(self) -> Optional[int]:
        return self._notificationId

    @property
    def groupId(self) -> int:
        return self._groupId

    @property
    def userId(self) -> int:
        return self._userId

    @property
    def meetingId(self) -> int:
        return self._meetingId

    @property
    def message(self) -> str:
        return self._message

    @property
    def sendAt(self) -> datetime:
        return self._sendAt

    @property
    def status(self) -> str:
        return self._status

    # Replace the message. Empty or only spaces is rejected.
    def setMessage(self, message: str) -> None:
        if not message or not message.strip():
            raise ValueError("Reminder message is required")
        self._message = message.strip()

    # Mark the reminder as sent
    def markSent(self) -> None:
        self._status = self.SENT