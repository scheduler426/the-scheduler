from __future__ import annotations

from scheduler.domain.meeting_poll import MeetingPoll
from scheduler.domain.scheduled_meeting import ScheduledMeeting
from scheduler.repositories.meeting_poll_repository import MeetingPollRepository
from scheduler.repositories.scheduled_meeting_repository import ScheduledMeetingRepository


class MeetingFinalizationService:
    def __init__(self, meetingRepo: ScheduledMeetingRepository, pollRepo: MeetingPollRepository):
        self._meetingRepo = meetingRepo
        self._pollRepo = pollRepo

    def confirmFinalTime(self, groupId: int, suggestionId: int, meetingName: str = "Group meeting") -> ScheduledMeeting:
        poll = self._pollRepo.findActiveByGroupId(groupId)
        if poll is None:
            raise LookupError("This group has no active poll")
        suggestions = poll.suggestions
        if suggestionId not in suggestions:
            raise LookupError(f"Suggestion {suggestionId} does not exist in this poll")
        slot = suggestions[suggestionId]
        meetingId = self._meetingRepo.save(ScheduledMeeting(None, groupId, meetingName, [slot]))
        self._pollRepo.save(MeetingPoll(poll.pollId, groupId, poll.closesAt, False, suggestions))
        return ScheduledMeeting(meetingId, groupId, meetingName, [slot])
