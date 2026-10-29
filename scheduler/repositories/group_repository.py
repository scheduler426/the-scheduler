from __future__ import annotations

from typing import Optional

from scheduler.domain.group import Group
from scheduler.infrastructure.duckdb_connection import DuckDBConnection


class GroupRepository:
    def __init__(self, db: DuckDBConnection):
        self._db = db

    def findById(self, id: int) -> Optional[Group]:
        row = self._db.sql("SELECT groupId, groupName, description FROM groups WHERE groupId = ?", [id]).fetchone()
        return Group(row[0], row[1], row[2] or "") if row else None

    def findAllByUserId(self, userId: int) -> list[Group]:
        rows = self._db.sql(
            "SELECT g.groupId, g.groupName, g.description FROM groups g "
            "JOIN groupRoster r ON r.groupId = g.groupId WHERE r.userId = ? ORDER BY g.groupName",
            [userId],
        ).fetchall()
        return [Group(row[0], row[1], row[2] or "") for row in rows]

    def save(self, group: Group) -> int:
        if group.groupId is None:
            return self._db.sql(
                "INSERT INTO groups (groupName, description) VALUES (?, ?) RETURNING groupId",
                [group.groupName, group.description],
            ).fetchone()[0]
        self._db.sql(
            "UPDATE groups SET groupName = ?, description = ? WHERE groupId = ?",
            [group.groupName, group.description, group.groupId],
        )
        return group.groupId

    def delete(self, id: int) -> None:
        pollIds = "SELECT pollId FROM meetingPolls WHERE groupId = ?"
        meetingIds = "SELECT meetingId FROM scheduledMeetings WHERE groupId = ?"
        self._db.sql(f"DELETE FROM votes WHERE pollId IN ({pollIds})", [id])
        self._db.sql(f"DELETE FROM pollSuggestions WHERE pollId IN ({pollIds})", [id])
        self._db.sql("DELETE FROM meetingPolls WHERE groupId = ?", [id])
        self._db.sql(f"DELETE FROM meetingSlots WHERE meetingId IN ({meetingIds})", [id])
        self._db.sql("DELETE FROM scheduledMeetings WHERE groupId = ?", [id])
        self._db.sql("DELETE FROM groupInvitations WHERE groupId = ?", [id])
        self._db.sql("DELETE FROM groupRoster WHERE groupId = ?", [id])
        self._db.sql("DELETE FROM groups WHERE groupId = ?", [id])
