from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from scheduler.domain.meeting_poll import MeetingPoll


class Vote:
    PREFERENCE_WEIGHTS = {"yes": 1.0, "maybe": 0.5, "no": 0.0}

    def __init__(self, voteId: Optional[int], pollId: int, userId: int, suggestionId: int, votePreference: str):
        self._validatePreference(votePreference)
        self._voteId = voteId
        self._pollId = pollId
        self._userId = userId
        self._suggestionId = suggestionId
        self._votePreference = votePreference

    @property
    def voteId(self) -> Optional[int]:
        return self._voteId

    @property
    def pollId(self) -> int:
        return self._pollId

    @property
    def userId(self) -> int:
        return self._userId

    @property
    def suggestionId(self) -> int:
        return self._suggestionId

    @property
    def votePreference(self) -> str:
        return self._votePreference

    def submitVote(self, poll: MeetingPoll) -> None:
        if not poll.isActive or datetime.now() >= poll.closesAt:
            raise ValueError("This poll is closed")
        if self._suggestionId not in poll.suggestions:
            raise LookupError(f"Suggestion {self._suggestionId} does not exist in this poll")

    def changeVote(self, suggestionId: int, votePreference: str) -> None:
        self._validatePreference(votePreference)
        self._suggestionId = suggestionId
        self._votePreference = votePreference

    @classmethod
    def _validatePreference(cls, votePreference: str) -> None:
        if votePreference not in cls.PREFERENCE_WEIGHTS:
            raise ValueError(f"votePreference must be one of {sorted(cls.PREFERENCE_WEIGHTS)}")
