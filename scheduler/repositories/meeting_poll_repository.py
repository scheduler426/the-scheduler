"""Storage contract for a meeting poll. Implementations only load and save.

VotingService, MeetingSuggestionService, and MeetingFinalizationService
depend on this interface. DuckDBMeetingPollRepository is the DuckDB
implementation. The interface does not tally votes or pick a meeting time.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from scheduler.domain.meeting_poll import MeetingPoll


class MeetingPollRepository(ABC):
    """Find, save, and delete a MeetingPoll without applying scheduling rules."""
    @abstractmethod
    def findActiveByGroupId(self, groupId: int) -> Optional[MeetingPoll]:
        """Return the group's active poll, or None."""
        ...

    @abstractmethod
    def findById(self, pollId: int) -> Optional[MeetingPoll]:
        """Return the poll, or None when the id is unknown."""
        ...

    @abstractmethod
    def save(self, poll: MeetingPoll) -> int:
        """Insert or update the poll and return its id."""
        ...

    @abstractmethod
    def delete(self, poll: MeetingPoll) -> None:
        """Remove the poll."""
        ...
