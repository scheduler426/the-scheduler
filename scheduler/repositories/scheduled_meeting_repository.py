from __future__ import annotations

from typing import Sequence

from scheduler.domain.scheduled_meeting import ScheduledMeeting
from scheduler.domain.time_slot import TimeSlot
from scheduler.infrastructure.duckdb_connection import DuckDBConnection


class ScheduledMeetingRepository:
    def __init__(self, db: DuckDBConnection):
        self._db = db

    def findAllByUserId(self, userId: int) -> list[ScheduledMeeting]:
        rows = self._db.sql(
            "SELECT m.meetingId, m.groupId, m.meetingName, m.status FROM scheduledMeetings m "
            "JOIN groupRoster r ON r.groupId = m.groupId WHERE r.userId = ? ORDER BY m.meetingId",
            [userId],
        ).fetchall()
        return [self._meetingFromRow(row) for row in rows]

    def save(self, meeting: ScheduledMeeting) -> int:
        meetingId = meeting.meetingId
        if meetingId is None:
            meetingId = self._db.sql(
                "INSERT INTO scheduledMeetings (groupId, meetingName, status) VALUES (?, ?, ?) RETURNING meetingId",
                [meeting.groupId, meeting.meetingName, meeting.status],
            ).fetchone()[0]
        else:
            self._db.sql(
                "UPDATE scheduledMeetings SET meetingName = ?, status = ? WHERE meetingId = ?",
                [meeting.meetingName, meeting.status, meetingId],
            )
        self._db.sql("DELETE FROM meetingSlots WHERE meetingId = ?", [meetingId])
        for slot in meeting.scheduledSlots:
            self._db.sql(
                "INSERT INTO meetingSlots (meetingId, startTime, endTime, cadence) VALUES (?, ?, ?, ?)",
                [meetingId, slot.startTime, slot.endTime, slot.cadence],
            )
        return meetingId

    def _meetingFromRow(self, row: Sequence) -> ScheduledMeeting:
        slotRows = self._db.sql(
            "SELECT startTime, endTime, cadence FROM meetingSlots WHERE meetingId = ? ORDER BY startTime", [row[0]]
        ).fetchall()
        return ScheduledMeeting(row[0], row[1], row[2], (TimeSlot(*slot) for slot in slotRows), row[3])
