"""Suggested meeting times for a group, plus the votes cast so far.

MeetingGenerator creates a poll. MeetingPollRepository loads its
suggestions and votes, and the constructor tallies those votes.
alreadyVoted holds user ids, not User objects. Choosing a winner and
closing the poll happen in other types.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from scheduler.domain.time_slot import TimeSlot
from scheduler.domain.vote import Vote


class MeetingPoll:
    """Suggestions keyed by id, a close time, and a tally of the votes it holds.

    tallyVotes scores each suggestion with Vote weights: yes is 1, maybe is
    0.5, and no is 0. The active flag is whatever the caller passed in.
    """
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
        """Suggestion id to total weight."""
        return dict(self._voteTally)

    @property
    def alreadyVoted(self) -> list[int]:
        """User ids that have a vote, in the order those votes were given."""
        return list(self._alreadyVoted)

    def tallyVotes(self) -> None:
        """Rebuild voteTally and alreadyVoted from the votes held on this poll."""
        tally = {suggestionId: 0.0 for suggestionId in self._suggestions}
        for vote in self._votes:
            if vote.suggestionId in tally:
                tally[vote.suggestionId] += Vote.PREFERENCE_WEIGHTS[vote.votePreference]
        self._voteTally = tally
        self._alreadyVoted = [vote.userId for vote in self._votes]
