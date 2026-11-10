# Lists a user's meetings that are still on (not cancelled).

from __future__ import annotations

from scheduler.domain.scheduled_meeting import ScheduledMeeting
from scheduler.repositories.scheduled_meeting_repository import ScheduledMeetingRepository


class MeetingRetrievalService:
    def __init__(self, meetingRepo: ScheduledMeetingRepository):
        self._meetingRepo = meetingRepo

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