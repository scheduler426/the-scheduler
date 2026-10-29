from __future__ import annotations

from typing import Optional

from scheduler.domain.vote import Vote
from scheduler.infrastructure.duckdb_connection import DuckDBConnection


class VoteRepository:
    def __init__(self, db: DuckDBConnection):
        self._db = db

    def findByPollAndUser(self, pollId: int, userId: int) -> Optional[Vote]:
        row = self._db.sql(
            "SELECT voteId, pollId, userId, suggestionId, votePreference FROM votes WHERE pollId = ? AND userId = ?",
            [pollId, userId],
        ).fetchone()
        return Vote(*row) if row else None

    def save(self, vote: Vote) -> None:
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
        self._db.sql("DELETE FROM votes WHERE pollId = ?", [pollId])
