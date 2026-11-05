"""Reads and writes groups and their member lists.

GroupService and GroupMembershipService call these methods. Membership is
the User-Group association, so it is stored here rather than in a separate
roster repository. delete clears votes, poll suggestions, polls, meeting
slots, meetings, invitations, and members before the group row. This class
does not check who requested a change.
"""

from __future__ import annotations

from typing import Optional

from scheduler.domain.group import Group
from scheduler.domain.user import User
from scheduler.infrastructure.database import Database


class GroupRepository:
    """Access to the groups and groupRoster tables through a Database.

    findAllByUserId returns groups whose roster includes that user.
    save inserts a group with no members; addMember adds them.
    """
    def __init__(self, db: Database):
        self._db = db

    def findById(self, id: int) -> Optional[Group]:
        row = self._db.sql("SELECT groupId, groupName, description FROM groups WHERE groupId = ?", [id]).fetchone()
        return Group(row[0], row[1], row[2] or "") if row else None

    def findAllByUserId(self, userId: int) -> list[Group]:
        """Return the groups this user belongs to, ordered by name."""
        rows = self._db.sql(
            "SELECT g.groupId, g.groupName, g.description FROM groups g "
            "JOIN groupRoster r ON r.groupId = g.groupId WHERE r.userId = ? ORDER BY g.groupName",
            [userId],
        ).fetchall()
        return [Group(row[0], row[1], row[2] or "") for row in rows]

    def findMembers(self, groupId: int) -> list[User]:
        """Return members' profile fields. Their availability schedules are not loaded."""
        rows = self._db.sql(
            "SELECT u.userId, u.email, u.passwordHash, u.firstName, u.lastName, u.allowEmailReminders "
            "FROM users u JOIN groupRoster r ON r.userId = u.userId WHERE r.groupId = ? "
            "ORDER BY u.lastName, u.firstName",
            [groupId],
        ).fetchall()
        return [User(*row[:5], bool(row[5])) for row in rows]

    def save(self, group: Group) -> int:
        """Insert or update the group and return its id."""
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

    def addMember(self, groupId: int, userId: int) -> None:
        """Add the membership if that pair is not already stored."""
        self._db.sql(
            "INSERT INTO groupRoster (groupId, userId) VALUES (?, ?) ON CONFLICT DO NOTHING", [groupId, userId]
        )

    def removeMember(self, groupId: int, userId: int) -> None:
        """Delete the membership. A missing pair leaves the table unchanged."""
        self._db.sql("DELETE FROM groupRoster WHERE groupId = ? AND userId = ?", [groupId, userId])

    def delete(self, id: int) -> None:
        """Delete the group and its polls, votes, meetings, invitations, and members."""
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
