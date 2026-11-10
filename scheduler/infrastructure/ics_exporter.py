# Turns a scheduled meeting into the text of an .ics calendar file.

from __future__ import annotations

from datetime import datetime

from scheduler.domain.scheduled_meeting import ScheduledMeeting


class IcsExporter:
    def __init__(self, version: str = "2.0"):
        self._version = version

    # Write one meeting as .ics bytes: one event per slot, lines ending in \r\n
    def exportMeetingToIcs(self, meeting: ScheduledMeeting) -> bytes:
        return self.exportMeetingsToIcs([meeting])

    # Write many meetings as one calendar: one event for every slot of every meeting
    def exportMeetingsToIcs(self, meetings: list[ScheduledMeeting]) -> bytes:
        lines = ["BEGIN:VCALENDAR", f"VERSION:{self._version}"]
        for meeting in meetings:
            for slot in meeting.scheduledSlots:
                lines.extend(self._eventLines(meeting, slot))
        lines.append("END:VCALENDAR")
        return ("\r\n".join(lines) + "\r\n").encode("utf-8")

    def _eventLines(self, meeting: ScheduledMeeting, slot) -> list[str]:
        lines = [
            "BEGIN:VEVENT",
            f"SUMMARY:{meeting.meetingName}",
            f"DTSTART:{self._formatTime(slot.startTime)}",
            f"DTEND:{self._formatTime(slot.endTime)}",
        ]
        if slot.cadence == "weekly":
            lines.append("RRULE:FREQ=WEEKLY")
        elif slot.cadence == "daily":
            lines.append("RRULE:FREQ=DAILY")
        lines.append("END:VEVENT")
        return lines

    # YYYYMMDDTHHMMSSZ from the stored time, with no timezone conversion
    def _formatTime(self, value: datetime) -> str:
        return value.strftime("%Y%m%dT%H%M%SZ")