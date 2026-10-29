from __future__ import annotations

from typing import Optional

from scheduler.domain.meeting_poll import MeetingPoll
from scheduler.domain.time_slot import TimeSlot
from scheduler.domain.vote import Vote
from scheduler.infrastructure.duckdb_connection import DuckDBConnection
from scheduler.repositories.meeting_poll_repository import MeetingPollRepository


class DuckDBMeetingPollRepository(MeetingPollRepository):
    def __init__(self, db: DuckDBConnection):
        self._db = db

    def findActiveByGroupId(self, groupId: int) -> Optional[MeetingPoll]:
        row = self._db.sql(
            "SELECT pollId FROM meetingPolls WHERE groupId = ? AND isActive ORDER BY pollId DESC LIMIT 1",
            [groupId],
        ).fetchone()
        return self.findById(row[0]) if row else None

    def findById(self, pollId: int) -> Optional[MeetingPoll]:
        row = self._db.sql(
            "SELECT pollId, groupId, closesAt, isActive FROM meetingPolls WHERE pollId = ?", [pollId]
        ).fetchone()
        if row is None:
            return None
        suggestionRows = self._db.sql(
            "SELECT suggestionId, startTime, endTime, cadence FROM pollSuggestions WHERE pollId = ?", [pollId]
        ).fetchall()
        voteRows = self._db.sql(
            "SELECT voteId, pollId, userId, suggestionId, votePreference FROM votes WHERE pollId = ?", [pollId]
        ).fetchall()
        return MeetingPoll(
            row[0],
            row[1],
            row[2],
            bool(row[3]),
            {suggestion[0]: TimeSlot(*suggestion[1:]) for suggestion in suggestionRows},
            [Vote(*vote) for vote in voteRows],
        )

    def save(self, poll: MeetingPoll) -> int:
        pollId = poll.pollId
        if pollId is None:
            pollId = self._db.sql(
                "INSERT INTO meetingPolls (groupId, closesAt, isActive) VALUES (?, ?, ?) RETURNING pollId",
                [poll.groupId, poll.closesAt, poll.isActive],
            ).fetchone()[0]
        else:
            self._db.sql(
                "UPDATE meetingPolls SET closesAt = ?, isActive = ? WHERE pollId = ?",
                [poll.closesAt, poll.isActive, pollId],
            )
        self._db.sql("DELETE FROM pollSuggestions WHERE pollId = ?", [pollId])
        for suggestionId, slot in poll.suggestions.items():
            self._db.sql(
                "INSERT INTO pollSuggestions (pollId, suggestionId, startTime, endTime, cadence) "
                "VALUES (?, ?, ?, ?, ?)",
                [pollId, suggestionId, slot.startTime, slot.endTime, slot.cadence],
            )
        return pollId

    def delete(self, poll: MeetingPoll) -> None:
        self._db.sql("DELETE FROM votes WHERE pollId = ?", [poll.pollId])
        self._db.sql("DELETE FROM pollSuggestions WHERE pollId = ?", [poll.pollId])
        self._db.sql("DELETE FROM meetingPolls WHERE pollId = ?", [poll.pollId])
