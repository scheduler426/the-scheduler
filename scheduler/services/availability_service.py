from __future__ import annotations

from typing import Iterable

from scheduler.domain.availability_schedule import AvailabilitySchedule
from scheduler.domain.time_slot import TimeSlot
from scheduler.repositories.availability_schedule_repository import AvailabilityScheduleRepository


class AvailabilityService:
    def __init__(self, scheduleRepo: AvailabilityScheduleRepository):
        self._scheduleRepo = scheduleRepo

    def getUserAvailability(self, userId: int) -> AvailabilitySchedule:
        return self._scheduleRepo.findByUserId(userId)

    def saveManualSchedule(self, userId: int, slots: Iterable[TimeSlot]) -> None:
        self._scheduleRepo.save(AvailabilitySchedule(userId, slots))
