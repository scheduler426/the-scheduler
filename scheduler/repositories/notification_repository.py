# Reads and writes meeting reminders in the notifications table.
# NotificationService-style callers use save to store a reminder and findDue to find the ones to send.
# This class does not send email or decide who may set a reminder.

from __future__ import annotations

from datetime import datetime

from scheduler.domain.notification import Notification
from scheduler.infrastructure.database import Database


class NotificationRepository:
    def __init__(self, db: Database):
        self._db = db

    # Insert a new reminder, or update the status of an existing one. Returns the id.
    def save(self, notification: Notification) -> int:
        if notification.notificationId is None:
            return self._db.sql(
                "INSERT INTO notifications (groupId, userId, meetingId, message, sendAt, status) "
                "VALUES (?, ?, ?, ?, ?, ?) RETURNING notificationId",
                [
                    notification.groupId,
                    notification.userId,
                    notification.meetingId,
                    notification.message,
                    notification.sendAt,
                    notification.status,
                ],
            ).fetchone()[0]
        self._db.sql(
            "UPDATE notifications SET status = ? WHERE notificationId = ?",
            [notification.status, notification.notificationId],
        )
        return notification.notificationId

    # Reminders that are still scheduled and whose send time has come
    def findDue(self, now: datetime) -> list[Notification]:
        rows = self._db.sql(
            "SELECT notificationId, groupId, userId, meetingId, message, sendAt, status "
            "FROM notifications WHERE status = 'scheduled' AND sendAt <= ? ORDER BY sendAt, notificationId",
            [now],
        ).fetchall()
        return [Notification(*row) for row in rows]