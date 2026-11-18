# Builds the text of scheduling emails.

from __future__ import annotations

from scheduler.domain.scheduled_meeting import ScheduledMeeting
from scheduler.domain.user import User


class SchedulingEmailTemplateFactory:
    def __init__(self):
        self.templateCache: dict[str, str] = {}

    # Text for "a meeting was set": the name, then each slot's start, end, and cadence
    def buildMeetingNoticeEmail(self, meeting: ScheduledMeeting) -> str:
        lines = [f'A meeting was set: "{meeting.meetingName}"', ""]
        for slot in meeting.scheduledSlots:
            lines.append(f"{slot.startTime} to {slot.endTime} ({slot.cadence})")
        return "\n".join(lines)

    # Text for "someone has a conflict": who, which meeting, and why
    def buildConflictNoticeEmail(self, meeting: ScheduledMeeting, reporter: User, reason: str) -> str:
        return (
            f'{reporter.firstName} {reporter.lastName} reported a schedule conflict for "{meeting.meetingName}".\n'
            f"Reason: {reason}"
        )