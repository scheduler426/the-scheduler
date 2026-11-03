"""Builds a new poll from group members' availability.

MeetingGenerator scores covered times. AvailabilityScheduleRepository loads
every member's schedule. MeetingPollRepository saves the poll.
generateSuggestions deletes the group's active poll first. This service
does not collect votes or confirm a meeting.
"""

from __future__ import annotations

from scheduler.domain.meeting_generator import MeetingGenerator
from scheduler.domain.meeting_poll import MeetingPoll
from scheduler.repositories.availability_schedule_repository import AvailabilityScheduleRepository
from scheduler.repositories.meeting_poll_repository import MeetingPollRepository


class MeetingSuggestionService:
    """Replaces the active poll with suggestions for the given constraints.

    constraints are passed to MeetingGenerator.setMeetingConstraints. If no
    member's availability covers a candidate, generateSuggestions raises
    after the previous poll has already been deleted.
    """
    def __init__(
        self,
        generator: MeetingGenerator,
        pollRepo: MeetingPollRepository,
        scheduleRepo: AvailabilityScheduleRepository,
    ):
        self._generator = generator
        self._pollRepo = pollRepo
        self._scheduleRepo = scheduleRepo

    def generateSuggestions(self, groupId: int, constraints: dict) -> MeetingPoll:
        """Delete the active poll, then save a new one built from the members' schedules."""
        self.resetActivePoll(groupId)
        self._generator.setMeetingConstraints(**constraints)
        slots = self._generator.generateMeetingSuggestions(self._scheduleRepo.findAllByGroupId(groupId))
        if not slots:
            raise ValueError("No member availability matches the requested constraints")
        pollId = self._pollRepo.save(self._generator.createMeetingPoll(slots, groupId))
        return self._pollRepo.findById(pollId)

    def resetActivePoll(self, groupId: int) -> None:
        """Delete the group's active poll, if any, and clear the generator's suggestions."""
        poll = self._pollRepo.findActiveByGroupId(groupId)
        if poll is not None:
            self._pollRepo.delete(poll)
        self._generator.resetMeetingSuggestions()
