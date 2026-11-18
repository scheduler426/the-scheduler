"""Reads and writes vote rows. Poll rules are applied before it is called.

VotingService checks membership and calls Vote.submitVote, then save.
clearByPollId deletes every vote for a poll. MeetingPollRepository
also deletes a poll's votes when the poll itself is deleted. This class
does not tally votes or decide who has voted.
"""

from __future__ import annotations

from typing import Optional

from scheduler.domain.vote import Vote
from scheduler.infrastructure.database import Database


class VoteRepository:
    """Access to the votes table through a Database.

    findByPollAndUser returns all of that user's votes for the poll, one per
    suggestion. save inserts a new row, or updates the row for the same
    poll, user, and suggestion.
    """
    def __init__(self, db: Database):
        self._db = db

    def findByPollAndUser(self, pollId: int, userId: int) -> list[Vote]:
        rows = self._db.sql(
            "SELECT voteId, pollId, userId, suggestionId, votePreference FROM votes WHERE pollId = ? AND userId = ?",
            [pollId, userId],
        ).fetchall()
        return [Vote(*row) for row in rows]

    def findByPollUserAndSuggestion(self, pollId: int, userId: int, suggestionId: int) -> Optional[Vote]:
        row = self._db.sql(
            "SELECT voteId, pollId, userId, suggestionId, votePreference FROM votes "
            "WHERE pollId = ? AND userId = ? AND suggestionId = ?",
            [pollId, userId, suggestionId],
        ).fetchone()
        return Vote(*row) if row else None

    def save(self, vote: Vote) -> None:
        """Insert a new vote, or update the row for the same poll, user, and suggestion."""
        self._db.sql(
            "INSERT INTO votes (pollId, userId, suggestionId, votePreference) VALUES (?, ?, ?, ?) "
            "ON CONFLICT (pollId, userId, suggestionId) DO UPDATE SET votePreference = excluded.votePreference",
            [vote.pollId, vote.userId, vote.suggestionId, vote.votePreference],
        )

    def clearByPollId(self, pollId: int) -> None:
        """Delete every vote stored for the poll."""
        self._db.sql("DELETE FROM votes WHERE pollId = ?", [pollId])