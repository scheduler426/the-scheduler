"""An offer for an email address to join a group.

GroupMembershipService builds an Invitation, usually with a seven-day
lifetime, and GroupInvitationRepository saves it. isExpired is the rule
kept on the invite itself. Sending the invite by email is outside this class.
"""

from __future__ import annotations

from datetime import datetime


class Invitation:
    """Who invited whom, the token, the status, and the expiry.

    Status is pending or accepted. Expiry is a timestamp chosen by the caller.
    """
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
        """True when the current time is at or past expiresAt."""
        return datetime.now() >= self._expiresAt
