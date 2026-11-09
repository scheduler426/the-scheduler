# Reads .ics calendar files into time slots.

from __future__ import annotations

from datetime import datetime

from scheduler.domain.calendar_parser import CalendarParser
from scheduler.domain.time_slot import TimeSlot


class IcsParser(CalendarParser):
    # Join any line that starts with a space or tab onto the line before it
    def _unfold(self, fileBytes: bytes) -> list[str]:
        lines = []
        for line in fileBytes.decode("utf-8").splitlines():
            if line[:1] in (" ", "\t") and lines:
                lines[-1] += line[1:]
            else:
                lines.append(line)
        return lines

    # True only if it looks like a calendar with at least one event
    def validateFormat(self, fileBytes: bytes) -> bool:
        text = "\n".join(self._unfold(fileBytes))
        return (
            "BEGIN:VCALENDAR" in text
            and "BEGIN:VEVENT" in text
            and "END:VEVENT" in text
        )

    # Turn 20260301T090000Z or 20260301T090000 into a datetime
    def _toDatetime(self, value: str) -> datetime:
        return datetime.strptime(value.rstrip("Z"), "%Y%m%dT%H%M%S")

    # Make one TimeSlot for each event that has a start and an end
    def parseToSlots(self, fileBytes: bytes) -> list[TimeSlot]:
        slots = []
        start = end = None
        for line in self._unfold(fileBytes):
            if line.startswith("BEGIN:VEVENT"):
                start = end = None
            elif line.startswith("DTSTART"):
                start = self._toDatetime(line.split(":", 1)[1])
            elif line.startswith("DTEND"):
                end = self._toDatetime(line.split(":", 1)[1])
            elif line.startswith("END:VEVENT"):
                # An event with no DTEND is skipped
                if start and end:
                    slots.append(TimeSlot(start, end, "once"))
        if not slots:
            raise ValueError("The calendar has no events with a start and end time")
        return slots