from __future__ import annotations

from datetime import datetime
from typing import Optional

from scheduler.domain.invitation import Invitation
from scheduler.infrastructure.duckdb_connection import DuckDBConnection


class GroupInvitationRepository:
    _COLUMNS = "groupId, inviterUserId, inviteToken, inviteeEmail, status, expiresAt"

    def __init__(self, db: DuckDBConnection):
        self._db = db

    def findByToken(self, token: str) -> Optional[Invitation]:
        row = self._db.sql(f"SELECT {self._COLUMNS} FROM groupInvitations WHERE inviteToken = ?", [token]).fetchone()
        return Invitation(*row) if row else None

    def findAllActiveByGroup(self, groupId: int) -> list[Invitation]:
        rows = self._db.sql(
            f"SELECT {self._COLUMNS} FROM groupInvitations WHERE groupId = ? AND status = ? AND expiresAt > ?",
            [groupId, Invitation.PENDING, datetime.now()],
        ).fetchall()
        return [Invitation(*row) for row in rows]

    def save(self, invite: Invitation) -> None:
        self._db.sql(
            f"INSERT OR REPLACE INTO groupInvitations ({self._COLUMNS}) VALUES (?, ?, ?, ?, ?, ?)",
            [
                invite.groupId,
                invite.inviterUserId,
                invite.inviteToken,
                invite.inviteeEmail,
                invite.status,
                invite.expiresAt,
            ],
        )
