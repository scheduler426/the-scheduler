"""Reads and writes vote rows. Poll rules are applied before it is called.

VotingService checks membership and calls Vote.submitVote, then save.
clearByPollId deletes every vote for a poll. DuckDBMeetingPollRepository
also deletes a poll's votes when the poll itself is deleted. This class
does not tally votes or decide who has voted.
"""

from __future__ import annotations

from typing import Optional

from scheduler.domain.vote import Vote
from scheduler.infrastructure.duckdb_connection import DuckDBConnection


class VoteRepository:
    """DuckDB access for the votes table through DuckDBConnection.

    findByPollAndUser returns that user's one vote for the poll. save
    inserts when voteId is missing and otherwise updates the suggestion
    and preference.
    """
    def __init__(self, db: DuckDBConnection):
        self._db = db

    def findByPollAndUser(self, pollId: int, userId: int) -> Optional[Vote]:
        row = self._db.sql(
            "SELECT voteId, pollId, userId, suggestionId, votePreference FROM votes WHERE pollId = ? AND userId = ?",
            [pollId, userId],
        ).fetchone()
        return Vote(*row) if row else None

    def save(self, vote: Vote) -> None:
        """Insert a new vote or update its suggestion and preference."""
        if vote.voteId is None:
            self._db.sql(
                "INSERT INTO votes (pollId, userId, suggestionId, votePreference) VALUES (?, ?, ?, ?)",
                [vote.pollId, vote.userId, vote.suggestionId, vote.votePreference],
            )
        else:
            self._db.sql(
                "UPDATE votes SET suggestionId = ?, votePreference = ? WHERE voteId = ?",
                [vote.suggestionId, vote.votePreference, vote.voteId],
            )

    def clearByPollId(self, pollId: int) -> None:
        """Delete every vote stored for the poll."""
        self._db.sql("DELETE FROM votes WHERE pollId = ?", [pollId])
