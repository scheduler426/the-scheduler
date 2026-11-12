# Lists a user's meetings that are still on (not cancelled).

from __future__ import annotations

from scheduler.domain.scheduled_meeting import ScheduledMeeting
from scheduler.repositories.scheduled_meeting_repository import ScheduledMeetingRepository
from scheduler.infrastructure.email_service import EmailService
from scheduler.infrastructure.ics_exporter import IcsExporter


class MeetingRetrievalService:
    def __init__(
        self,
        meetingRepo: ScheduledMeetingRepository,
        emailService: EmailService,
        icsExporter: IcsExporter,
    ):
        self._meetingRepo = meetingRepo
        self._emailService = emailService
        self._icsExporter = icsExporter

    # findAllByUserId includes cancelled meetings, so keep only the scheduled ones
    def getUserMeetings(self, userId: int) -> list[ScheduledMeeting]:
        return [
            meeting
            for meeting in self._meetingRepo.findAllByUserId(userId)
            if meeting.status == ScheduledMeeting.SCHEDULED
        ]

    # Look in the user's own meetings, so a cancelled meeting or another group's meeting is not found
    def getMeetingForUser(self, userId: int, meetingId: int) -> ScheduledMeeting:
        for meeting in self.getUserMeetings(userId):
            if meeting.meetingId == meetingId:
                return meeting
        raise LookupError("Meeting not found")
    
    # Email the user's whole meeting schedule, as one .ics file, to any address. Nothing is stored.
    def shareUserMeetings(self, userId: int, recipientEmail: str) -> None:
        meetings = self.getUserMeetings(userId)
        if not meetings:
            raise ValueError("There is no active meeting to share")
        # Needs text before the @ and a "." after it. Any domain is allowed.
        local, at, domain = (recipientEmail or "").partition("@")
        if not local or not at or "." not in domain:
            raise ValueError("A valid email address is required")
        self._emailService.sendEmailWithAttachment(
            recipientEmail,
            "Shared meeting schedule",
            f"{len(meetings)} meetings are attached.",
            "meetings.ics",
            self._icsExporter.exportMeetingsToIcs(meetings),
        )