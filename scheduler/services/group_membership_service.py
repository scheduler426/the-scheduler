from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from scheduler.domain.invitation import Invitation
from scheduler.repositories.group_invitation_repository import GroupInvitationRepository
from scheduler.repositories.group_roster_repository import GroupRosterRepository


class GroupMembershipService:
    def __init__(
        self,
        rosterRepo: GroupRosterRepository,
        inviteRepo: GroupInvitationRepository,
        inviteValidity: timedelta = timedelta(days=7),
    ):
        self._rosterRepo = rosterRepo
        self._inviteRepo = inviteRepo
        self._inviteValidity = inviteValidity

    def inviteUser(self, groupId: int, email: str, inviterUserId: int) -> Invitation:
        if not self._isMember(groupId, inviterUserId):
            raise PermissionError("Only group members can send invitations")
        invitation = Invitation(
            groupId,
            inviterUserId,
            secrets.token_urlsafe(32),
            email.strip().lower(),
            Invitation.PENDING,
            datetime.now() + self._inviteValidity,
        )
        self._inviteRepo.save(invitation)
        return invitation

    def processInviteLink(self, token: str, userId: int) -> None:
        invitation = self._inviteRepo.findByToken(token)
        if invitation is None:
            raise LookupError("Invitation not found")
        if invitation.status != Invitation.PENDING:
            raise ValueError(f"Invitation has already been {invitation.status}")
        if invitation.isExpired():
            raise ValueError("Invitation has expired")
        self._rosterRepo.save(invitation.groupId, userId)
        self._inviteRepo.save(
            Invitation(
                invitation.groupId,
                invitation.inviterUserId,
                invitation.inviteToken,
                invitation.inviteeEmail,
                Invitation.ACCEPTED,
                invitation.expiresAt,
            )
        )

    def removeMemberFromRoster(self, groupId: int, targetUserId: int) -> None:
        if not self._isMember(groupId, targetUserId):
            raise LookupError("User is not a member of this group")
        self._rosterRepo.remove(groupId, targetUserId)

    def leaveGroup(self, userId: int, groupId: int) -> None:
        self.removeMemberFromRoster(groupId, userId)

    def _isMember(self, groupId: int, userId: int) -> bool:
        return any(member.userId == userId for member in self._rosterRepo.findByGroupId(groupId))
