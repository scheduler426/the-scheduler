"""Reads and writes group membership rows and nothing else.

GroupService adds the creator. GroupMembershipService adds someone who
accepts an invite and removes someone who leaves. This repository does not
inspect invitations or decide whether a removal is allowed.
"""

from __future__ import annotations

from scheduler.domain.user import User
from scheduler.infrastructure.duckdb_connection import DuckDBConnection


class GroupRosterRepository:
    """DuckDB access for groupRoster through DuckDBConnection.

    findByGroupId returns each member's profile. save adds a pair and
    ignores a duplicate. remove deletes one pair.
    """
    def __init__(self, db: DuckDBConnection):
        self._db = db

    def findByGroupId(self, groupId: int) -> list[User]:
        """Return members' profile fields. Their availability schedules are not loaded."""
        rows = self._db.sql(
            "SELECT u.userId, u.email, u.passwordHash, u.firstName, u.lastName, u.allowEmailReminders "
            "FROM users u JOIN groupRoster r ON r.userId = u.userId WHERE r.groupId = ? "
            "ORDER BY u.lastName, u.firstName",
            [groupId],
        ).fetchall()
        return [User(*row[:5], bool(row[5])) for row in rows]

    def save(self, groupId: int, userId: int) -> None:
        """Add the membership if that pair is not already stored."""
        self._db.sql("INSERT OR IGNORE INTO groupRoster (groupId, userId) VALUES (?, ?)", [groupId, userId])

    def remove(self, groupId: int, userId: int) -> None:
        """Delete the membership. A missing pair leaves the table unchanged."""
        self._db.sql("DELETE FROM groupRoster WHERE groupId = ? AND userId = ?", [groupId, userId])
