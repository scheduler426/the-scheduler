from __future__ import annotations

from scheduler.domain.meeting_generator import MeetingGenerator
from scheduler.domain.meeting_poll import MeetingPoll
from scheduler.repositories.availability_schedule_repository import AvailabilityScheduleRepository
from scheduler.repositories.meeting_poll_repository import MeetingPollRepository


class MeetingSuggestionService:
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
        self.resetActivePoll(groupId)
        self._generator.setMeetingConstraints(**constraints)
        slots = self._generator.generateMeetingSuggestions(self._scheduleRepo.findAllByGroupId(groupId))
        if not slots:
            raise ValueError("No member availability matches the requested constraints")
        pollId = self._pollRepo.save(self._generator.createMeetingPoll(slots, groupId))
        return self._pollRepo.findById(pollId)

    def resetActivePoll(self, groupId: int) -> None:
        poll = self._pollRepo.findActiveByGroupId(groupId)
        if poll is not None:
            self._pollRepo.delete(poll)
        self._generator.resetMeetingSuggestions()
