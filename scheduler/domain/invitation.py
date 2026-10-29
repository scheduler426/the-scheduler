from __future__ import annotations

from datetime import datetime


class Invitation:
    PENDING = "pending"
    ACCEPTED = "accepted"

    def __init__(
        self,
        groupId: int,
        inviterUserId: int,
        inviteToken: str,
        inviteeEmail: str,
        status: str,
        expiresAt: datetime,
    ):
        self._groupId = groupId
        self._inviterUserId = inviterUserId
        self._inviteToken = inviteToken
        self._inviteeEmail = inviteeEmail
        self._status = status
        self._expiresAt = expiresAt

    @property
    def groupId(self) -> int:
        return self._groupId

    @property
    def inviterUserId(self) -> int:
        return self._inviterUserId

    @property
    def inviteToken(self) -> str:
        return self._inviteToken

    @property
    def inviteeEmail(self) -> str:
        return self._inviteeEmail

    @property
    def status(self) -> str:
        return self._status

    @property
    def expiresAt(self) -> datetime:
        return self._expiresAt

    def isExpired(self) -> bool:
        return datetime.now() >= self._expiresAt
