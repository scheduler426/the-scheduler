from __future__ import annotations

from scheduler.domain.user import User
from scheduler.infrastructure.duckdb_connection import DuckDBConnection


class GroupRosterRepository:
    def __init__(self, db: DuckDBConnection):
        self._db = db

    def findByGroupId(self, groupId: int) -> list[User]:
        rows = self._db.sql(
            "SELECT u.userId, u.email, u.passwordHash, u.firstName, u.lastName, u.allowEmailReminders "
            "FROM users u JOIN groupRoster r ON r.userId = u.userId WHERE r.groupId = ? "
            "ORDER BY u.lastName, u.firstName",
            [groupId],
        ).fetchall()
        return [User(*row[:5], bool(row[5])) for row in rows]

    def save(self, groupId: int, userId: int) -> None:
        self._db.sql("INSERT OR IGNORE INTO groupRoster (groupId, userId) VALUES (?, ?)", [groupId, userId])

    def remove(self, groupId: int, userId: int) -> None:
        self._db.sql("DELETE FROM groupRoster WHERE groupId = ? AND userId = ?", [groupId, userId])
