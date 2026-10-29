from __future__ import annotations

from scheduler.domain.availability_schedule import AvailabilitySchedule
from scheduler.domain.time_slot import TimeSlot
from scheduler.infrastructure.duckdb_connection import DuckDBConnection


class AvailabilityScheduleRepository:
    def __init__(self, db: DuckDBConnection):
        self._db = db

    def findByUserId(self, userId: int) -> AvailabilitySchedule:
        rows = self._db.sql(
            "SELECT startTime, endTime, cadence FROM availabilitySlots WHERE userId = ? ORDER BY startTime",
            [userId],
        ).fetchall()
        return AvailabilitySchedule(userId, (TimeSlot(*row) for row in rows))

    def findAllByGroupId(self, groupId: int) -> list[AvailabilitySchedule]:
        rows = self._db.sql("SELECT userId FROM groupRoster WHERE groupId = ?", [groupId]).fetchall()
        return [self.findByUserId(row[0]) for row in rows]

    def save(self, schedule: AvailabilitySchedule) -> None:
        if schedule.userId is None:
            raise ValueError("Cannot save a schedule that is not tied to a user")
        self._db.sql("DELETE FROM availabilitySlots WHERE userId = ?", [schedule.userId])
        for slot in schedule.retrieveAvailabilitySchedule():
            self._db.sql(
                "INSERT INTO availabilitySlots (userId, startTime, endTime, cadence) VALUES (?, ?, ?, ?)",
                [schedule.userId, slot.startTime, slot.endTime, slot.cadence],
            )
