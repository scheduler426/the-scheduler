"""Invites someone to a group and changes the roster.

GroupInvitationRepository stores the invite. GroupRepository adds or
removes the member. inviteUser saves a pending invite that expires in seven
days. The invite is saved, and no mail is sent. processInviteLink accepts
a token that is still pending and unexpired.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from scheduler.domain.invitation import Invitation
from scheduler.repositories.group_invitation_repository import GroupInvitationRepository
from scheduler.repositories.group_repository import GroupRepository


class GroupMembershipService:
    """Invite, accept, leave, and remove, using the group and invitation repositories.

    The inviter must already be a member. Accepting adds the given user id
    to the roster and marks the invite accepted. This service does not check
    that the user's email is the invited address, and it does not build or
    send an email.
    """
    def __init__(
        self,
        groupRepo: GroupRepository,
        inviteRepo: GroupInvitationRepository,
        inviteValidity: timedelta = timedelta(days=7),
    ):
        self._groupRepo = groupRepo
        self._inviteRepo = inviteRepo
        self._inviteValidity = inviteValidity

    def inviteUser(self, groupId: int, email: str, inviterUserId: int) -> Invitation:
        """Save a pending invite that lasts seven days and return it. No message is sent."""
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
        """Add userId to the group and mark the invite accepted when it is still pending."""
        invitation = self._inviteRepo.findByToken(token)
        if invitation is None:
            raise LookupError("Invitation not found")
        if invitation.status != Invitation.PENDING:
            raise ValueError(f"Invitation has already been {invitation.status}")
        if invitation.isExpired():
            raise ValueError("Invitation has expired")
        self._groupRepo.addMember(invitation.groupId, userId)
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
        """Drop targetUserId from the roster. There is no separate owner check."""
        if not self._isMember(groupId, targetUserId):
            raise LookupError("User is not a member of this group")
        self._groupRepo.removeMember(groupId, targetUserId)

    def leaveGroup(self, userId: int, groupId: int) -> None:
        self.removeMemberFromRoster(groupId, userId)

    def _isMember(self, groupId: int, userId: int) -> bool:
        return self._groupRepo.isMember(groupId, userId)
