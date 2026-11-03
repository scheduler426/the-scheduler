"""The times one user has marked as free.

AvailabilitySchedule holds TimeSlot values. AvailabilityService and
AvailabilityScheduleRepository move that list to and from storage.
Overlap checks stay on TimeSlot. This class does not parse a calendar file.
"""

from __future__ import annotations

from typing import Iterable, Optional

from scheduler.domain.time_slot import TimeSlot


class AvailabilitySchedule:
    """In-memory free slots for one user id.

    Reading returns a copy. Updating replaces the whole list, and clearing
    empties it. Callers persist the result through the schedule repository.
    """
    def __init__(self, userId: Optional[int], availableSlots: Optional[Iterable[TimeSlot]] = None):
        self._userId = userId
        self._availableSlots: list[TimeSlot] = list(availableSlots or [])

    @property
    def userId(self) -> Optional[int]:
        return self._userId

    def retrieveAvailabilitySchedule(self) -> list[TimeSlot]:
        """Return a copy of the free slots."""
        return list(self._availableSlots)

    def updateAvailabilitySchedule(self, slots: Iterable[TimeSlot]) -> None:
        """Replace every stored slot with slots."""
        self._availableSlots = list(slots)

    def clearAvailabilitySchedule(self) -> None:
        self._availableSlots.clear()
