from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional

from scheduler.domain.meeting_poll import MeetingPoll


class MeetingPollRepository(ABC):
    @abstractmethod
    def findActiveByGroupId(self, groupId: int) -> Optional[MeetingPoll]:
        ...

    @abstractmethod
    def findById(self, pollId: int) -> Optional[MeetingPoll]:
        ...

    @abstractmethod
    def save(self, poll: MeetingPoll) -> int:
        ...

    @abstractmethod
    def delete(self, poll: MeetingPoll) -> None:
        ...
