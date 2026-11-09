from __future__ import annotations

from datetime import datetime
from typing import Iterable

from scheduler.domain.availability_schedule import AvailabilitySchedule
from scheduler.domain.calendar_parser import CalendarParser
from scheduler.domain.external_calendar_file import ExternalCalendarFile
from scheduler.domain.time_slot import TimeSlot
from scheduler.repositories.availability_schedule_repository import AvailabilityScheduleRepository


class AvailabilityService:
    """Loads and saves availability, either typed in by hand or imported from a calendar file."""
    def __init__(self, scheduleRepo: AvailabilityScheduleRepository, parser: CalendarParser):
        self._scheduleRepo = scheduleRepo
        self._parser = parser

    def getUserAvailability(self, userId: int) -> AvailabilitySchedule:
        return self._scheduleRepo.findByUserId(userId)

    def saveManualSchedule(self, userId: int, slots: Iterable[TimeSlot]) -> None:
        self._scheduleRepo.save(AvailabilitySchedule(userId, slots))

    def importIcsCalendar(self, userId: int, fileName: str, rawFileBytes: bytes) -> None:
        file = ExternalCalendarFile(fileName, len(rawFileBytes), rawFileBytes, datetime.now())

        # Save nothing if the file is not a valid calendar
        if not self._parser.validateFormat(file.fileContent):
            raise ValueError("The file is not a valid calendar")
        
        slots = self._parser.parseToSlots(file.fileContent)

        # save replaces the user's old slots
        self._scheduleRepo.save(AvailabilitySchedule(userId, slots))