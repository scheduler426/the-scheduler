from __future__ import annotations

from scheduler.domain.meeting_poll import MeetingPoll
from scheduler.domain.scheduled_meeting import ScheduledMeeting
from scheduler.infrastructure.email_service import MailDeliveryError
from scheduler.repositories.group_repository import GroupRepository
from scheduler.repositories.meeting_poll_repository import MeetingPollRepository
from scheduler.repositories.scheduled_meeting_repository import ScheduledMeetingRepository
from scheduler.services.group_notification_service import GroupNotificationService


class MeetingFinalizationService:
    """Saves one chosen slot as a meeting, closes the poll, and emails the group."""
    def __init__(
        self,
        meetingRepo: ScheduledMeetingRepository,
        pollRepo: MeetingPollRepository,
        notifier: GroupNotificationService,
        groupRepo: GroupRepository,
    ):
        self._meetingRepo = meetingRepo
        self._pollRepo = pollRepo
        self._notifier = notifier
        self._groupRepo = groupRepo

    def confirmFinalTime(
        self, groupId: int, suggestionId: int, userId: int, meetingName: str = "Group meeting"
    ) -> ScheduledMeeting:
        if not self._groupRepo.isMember(groupId, userId):
            raise PermissionError("Only group members can confirm a meeting")
        poll = self._pollRepo.findActiveByGroupId(groupId)
        if poll is None:
            raise LookupError("This group has no active poll")
        suggestions = poll.suggestions
        # With no suggestionId, pick the top-voted one. A tie goes to the earlier start time.
        if suggestionId is None:
            tally = poll.voteTally
            best = max(
                suggestions,
                key=lambda sid: (tally.get(sid, 0), -suggestions[sid].startTime.timestamp()),
            )
            if tally.get(best, 0) == 0:
                raise ValueError("No suggestion has a yes or maybe vote")
            suggestionId = best
        if suggestionId not in suggestions:
            raise LookupError(f"Suggestion {suggestionId} does not exist in this poll")
        slot = suggestions[suggestionId]
        meetingId = self._meetingRepo.save(ScheduledMeeting(None, groupId, meetingName, [slot]))
        self._pollRepo.save(MeetingPoll(poll.pollId, groupId, poll.closesAt, False, suggestions))
        meeting = ScheduledMeeting(meetingId, groupId, meetingName, [slot])
        memberIds = [member.userId for member in self._groupRepo.findMembers(groupId)]
        message = f'"{meetingName}" is set for {slot.startTime} to {slot.endTime} ({slot.cadence}).'
        try:
            self._notifier.dispatchManualReminder(groupId, memberIds, message)
        except MailDeliveryError:
            raise MailDeliveryError(f"Meeting {meetingId} was saved but the notice was not sent")
        return meeting