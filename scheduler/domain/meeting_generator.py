"""Finds meeting times that members' availability can cover.

MeetingSuggestionService supplies constraints and the group's schedules,
then saves the MeetingPoll this generator builds. The generator does not
read DuckDB. It asks TimeSlot.covers and TimeSlot.overlaps rather than
reimplementing them. With no close time, the poll closes in two days.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable, Iterator, Optional

from scheduler.domain.availability_schedule import AvailabilitySchedule
from scheduler.domain.meeting_poll import MeetingPoll
from scheduler.domain.time_slot import TimeSlot


class MeetingGenerator:
    """Turns a search window into a few non-overlapping suggestions.

    A candidate counts when at least one schedule has a slot that covers it.
    Higher coverage comes first. A candidate that overlaps a slot already
    chosen is dropped. createMeetingPoll numbers the remaining slots from 1.
    """
    DEFAULT_POLL_DURATION = timedelta(days=2)

    def __init__(self):
        self._suggestedMeetings: list[TimeSlot] = []
        self._constraints: Optional[dict] = None

    def resetMeetingSuggestions(self) -> None:
        """Drop suggestions held on this generator. A saved poll is left as it is."""
        self._suggestedMeetings = []

    def setMeetingConstraints(
        self,
        windowStart: datetime,
        windowEnd: datetime,
        durationMinutes: int = 60,
        stepMinutes: int = 30,
        maxSuggestions: int = 5,
        pollClosesAt: Optional[datetime] = None,
    ) -> None:
        """Remember the window, length, step, suggestion cap, and optional close time."""
        if windowEnd <= windowStart:
            raise ValueError("windowEnd must be after windowStart")
        if durationMinutes <= 0 or stepMinutes <= 0 or maxSuggestions <= 0:
            raise ValueError("durationMinutes, stepMinutes and maxSuggestions must be positive")
        self._constraints = {
            "windowStart": windowStart,
            "windowEnd": windowEnd,
            "duration": timedelta(minutes=durationMinutes),
            "step": timedelta(minutes=stepMinutes),
            "maxSuggestions": maxSuggestions,
            "pollClosesAt": pollClosesAt,
        }

    def generateMeetingSuggestions(self, availabilitySchedules: Iterable[AvailabilitySchedule]) -> list[TimeSlot]:
        """Return the chosen slots, best coverage first, and remember them on this generator."""
        if self._constraints is None:
            raise ValueError("Meeting constraints must be set before generating suggestions")
        schedules = list(availabilitySchedules)
        scored = []
        for candidate in self._candidateSlots():
            score = sum(1 for schedule in schedules if self._isAvailable(schedule, candidate))
            if score:
                scored.append((score, candidate))
        scored.sort(key=lambda entry: (-entry[0], entry[1].startTime))
        chosen: list[TimeSlot] = []
        for _, candidate in scored:
            if len(chosen) == self._constraints["maxSuggestions"]:
                break
            if not any(candidate.overlaps(existing) for existing in chosen):
                chosen.append(candidate)
        self._suggestedMeetings = chosen
        return list(chosen)

    def createMeetingPoll(self, slots: Iterable[TimeSlot], groupId: int) -> MeetingPoll:
        """Build an active poll for groupId. It closes in two days when no close time was set."""
        closesAt = self._constraints["pollClosesAt"] if self._constraints else None
        suggestions = {suggestionId: slot for suggestionId, slot in enumerate(slots, start=1)}
        return MeetingPoll(None, groupId, closesAt or datetime.now() + self.DEFAULT_POLL_DURATION, True, suggestions)

    def _candidateSlots(self) -> Iterator[TimeSlot]:
        current = self._constraints["windowStart"]
        duration = self._constraints["duration"]
        while current + duration <= self._constraints["windowEnd"]:
            yield TimeSlot(current, current + duration)
            current += self._constraints["step"]

    @staticmethod
    def _isAvailable(schedule: AvailabilitySchedule, candidate: TimeSlot) -> bool:
        return any(slot.covers(candidate) for slot in schedule.retrieveAvailabilitySchedule())
