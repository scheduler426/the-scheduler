"""Reads and writes availability slots for users.

AvailabilityService loads and saves one user's schedule.
MeetingSuggestionService loads every member's schedule through
findAllByGroupId. save deletes the user's current slots and inserts the
ones on the schedule. Overlaps are not judged here, and calendar files
are not parsed here.
"""

from __future__ import annotations

from scheduler.domain.availability_schedule import AvailabilitySchedule
from scheduler.domain.time_slot import TimeSlot
from scheduler.infrastructure.database import Database


class AvailabilityScheduleRepository:
    """Access to availabilitySlots through a Database."""
    def __init__(self, db: Database):
        self._db = db

    def findByUserId(self, userId: int) -> AvailabilitySchedule:
        """Return the user's slots, or an empty schedule when none are stored."""
        rows = self._db.sql(
            "SELECT startTime, endTime, cadence FROM availabilitySlots WHERE userId = ? ORDER BY startTime",
            [userId],
        ).fetchall()
        return AvailabilitySchedule(userId, (TimeSlot(*row) for row in rows))

    def findAllByGroupId(self, groupId: int) -> list[AvailabilitySchedule]:
        """Return one schedule for each member of the group."""
        rows = self._db.sql("SELECT userId FROM groupRoster WHERE groupId = ?", [groupId]).fetchall()
        return [self.findByUserId(row[0]) for row in rows]

    def save(self, schedule: AvailabilitySchedule) -> None:
        """Replace all of the user's slots with the schedule's current list."""
        if schedule.userId is None:
            raise ValueError("Cannot save a schedule that is not tied to a user")
        self._db.sql("DELETE FROM availabilitySlots WHERE userId = ?", [schedule.userId])
        for slot in schedule.retrieveAvailabilitySchedule():
            self._db.sql(
                "INSERT INTO availabilitySlots (userId, startTime, endTime, cadence) VALUES (?, ?, ?, ?)",
                [schedule.userId, slot.startTime, slot.endTime, slot.cadence],
            )
