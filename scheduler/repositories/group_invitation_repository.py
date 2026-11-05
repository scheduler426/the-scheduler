"""Reads and writes invitation rows. Expiry rules live on Invitation.

GroupMembershipService saves an invite and later marks it accepted.
findAllActiveByGroup returns pending rows whose expiresAt is still ahead.
This repository does not send mail. GroupRepository removes a group's
invites when that group is deleted.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from scheduler.domain.invitation import Invitation
from scheduler.infrastructure.database import Database


class GroupInvitationRepository:
    """Access to groupInvitations through a Database.

    save inserts the invite or replaces the row with the same token.
    """
    _COLUMNS = "groupId, inviterUserId, inviteToken, inviteeEmail, status, expiresAt"

    def __init__(self, db: Database):
        self._db = db

    def findByToken(self, token: str) -> Optional[Invitation]:
        """Return the invite for this token, or None."""
        row = self._db.sql(f"SELECT {self._COLUMNS} FROM groupInvitations WHERE inviteToken = ?", [token]).fetchone()
        return Invitation(*row) if row else None

    def findAllActiveByGroup(self, groupId: int) -> list[Invitation]:
        """Return pending, unexpired invites for the group."""
        rows = self._db.sql(
            f"SELECT {self._COLUMNS} FROM groupInvitations WHERE groupId = ? AND status = ? AND expiresAt > ?",
            [groupId, Invitation.PENDING, datetime.now()],
        ).fetchall()
        return [Invitation(*row) for row in rows]

    def save(self, invite: Invitation) -> None:
        """Insert the invite or replace the row that already uses its token."""
        self._db.sql(
            f"INSERT INTO groupInvitations ({self._COLUMNS}) VALUES (?, ?, ?, ?, ?, ?) "
            "ON CONFLICT (inviteToken) DO UPDATE SET groupId = excluded.groupId, "
            "inviterUserId = excluded.inviterUserId, inviteeEmail = excluded.inviteeEmail, "
            "status = excluded.status, expiresAt = excluded.expiresAt",
            [
                invite.groupId,
                invite.inviterUserId,
                invite.inviteToken,
                invite.inviteeEmail,
                invite.status,
                invite.expiresAt,
            ],
        )
