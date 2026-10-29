from __future__ import annotations

from typing import Iterable, Optional

from scheduler.domain.time_slot import TimeSlot


class AvailabilitySchedule:
    def __init__(self, userId: Optional[int], availableSlots: Optional[Iterable[TimeSlot]] = None):
        self._userId = userId
        self._availableSlots: list[TimeSlot] = list(availableSlots or [])

    @property
    def userId(self) -> Optional[int]:
        return self._userId

    def retrieveAvailabilitySchedule(self) -> list[TimeSlot]:
        return list(self._availableSlots)

    def updateAvailabilitySchedule(self, slots: Iterable[TimeSlot]) -> None:
        self._availableSlots = list(slots)

    def clearAvailabilitySchedule(self) -> None:
        self._availableSlots.clear()
