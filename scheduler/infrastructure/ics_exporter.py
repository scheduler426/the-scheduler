# Turns a scheduled meeting into the text of an .ics calendar file.

from __future__ import annotations

from datetime import datetime

from scheduler.domain.scheduled_meeting import ScheduledMeeting


class IcsExporter:
    def __init__(self, version: str = "2.0"):
        self._version = version

    # Write the meeting as .ics bytes: one event per slot, lines ending in \r\n
    def exportMeetingToIcs(self, meeting: ScheduledMeeting) -> bytes:
        lines = ["BEGIN:VCALENDAR", f"VERSION:{self._version}"]
        for slot in meeting.scheduledSlots:
            lines.append("BEGIN:VEVENT")
            lines.append(f"SUMMARY:{meeting.meetingName}")
            lines.append(f"DTSTART:{self._formatTime(slot.startTime)}")
            lines.append(f"DTEND:{self._formatTime(slot.endTime)}")
            if slot.cadence == "weekly":
                lines.append("RRULE:FREQ=WEEKLY")
            elif slot.cadence == "daily":
                lines.append("RRULE:FREQ=DAILY")
            lines.append("END:VEVENT")
        lines.append("END:VCALENDAR")
        return ("\r\n".join(lines) + "\r\n").encode("utf-8")

    # YYYYMMDDTHHMMSSZ from the stored time, with no timezone conversion
    def _formatTime(self, value: datetime) -> str:
        return value.strftime("%Y%m%dT%H%M%SZ")