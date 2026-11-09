from __future__ import annotations

from abc import ABC, abstractmethod

from scheduler.domain.time_slot import TimeSlot


class CalendarParser(ABC):

    @abstractmethod
    def validateFormat(self, fileBytes: bytes) -> bool:
        # Return True if fileBytes is a valid file for this parser
        pass

    @abstractmethod
    def parseToSlots(self, fileBytes: bytes) -> list[TimeSlot]:
        # Return the file's events as a list of TimeSlot objects.
        pass