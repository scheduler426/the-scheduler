from __future__ import annotations

from datetime import datetime
from typing import Optional

from scheduler.domain.time_slot import TimeSlot
from scheduler.domain.vote import Vote


class MeetingPoll:
    def __init__(
        self,
        pollId: Optional[int],
        groupId: int,
        closesAt: datetime,
        isActive: bool = True,
        suggestions: Optional[dict[int, TimeSlot]] = None,
        votes: Optional[list[Vote]] = None,
    ):
        self._pollId = pollId
        self._groupId = groupId
        self._closesAt = closesAt
        self._isActive = isActive
        self._suggestions: dict[int, TimeSlot] = dict(suggestions or {})
        self._votes: list[Vote] = list(votes or [])
        self._voteTally: dict[int, float] = {}
        self._alreadyVoted: list[int] = []
        self.tallyVotes()

    @property
    def pollId(self) -> Optional[int]:
        return self._pollId

    @property
    def groupId(self) -> int:
        return self._groupId

    @property
    def closesAt(self) -> datetime:
        return self._closesAt

    @property
    def isActive(self) -> bool:
        return self._isActive

    @property
    def suggestions(self) -> dict[int, TimeSlot]:
        return dict(self._suggestions)

    @property
    def voteTally(self) -> dict[int, float]:
        return dict(self._voteTally)

    @property
    def alreadyVoted(self) -> list[int]:
        return list(self._alreadyVoted)

    def tallyVotes(self) -> None:
        tally = {suggestionId: 0.0 for suggestionId in self._suggestions}
        for vote in self._votes:
            if vote.suggestionId in tally:
                tally[vote.suggestionId] += Vote.PREFERENCE_WEIGHTS[vote.votePreference]
        self._voteTally = tally
        self._alreadyVoted = [vote.userId for vote in self._votes]
