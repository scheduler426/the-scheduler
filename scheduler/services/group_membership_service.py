"""Invites someone to a group and changes the roster.

GroupInvitationRepository stores the invite. GroupRepository adds or
removes the member. inviteUser saves a pending invite that expires in seven
days and emails the invitation. processInviteLink accepts a token that is
still pending and unexpired.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from scheduler.domain.invitation import Invitation
from scheduler.infrastructure.email_service import EmailService, MailDeliveryError
from scheduler.infrastructure.group_email_template_factory import GroupEmailTemplateFactory
from scheduler.repositories.group_invitation_repository import GroupInvitationRepository
from scheduler.repositories.group_repository import GroupRepository
from scheduler.repositories.user_repository import UserRepository


class InvitationMailDeliveryError(MailDeliveryError):
    """An invitation was saved, but delivery to its invitee failed."""

    def __init__(self, invitation: Invitation):
        self.inviteToken = invitation.inviteToken
        self.inviteeEmail = invitation.inviteeEmail
        super().__init__(f"Invitation {self.inviteToken} was saved but the email was not sent")


class GroupMembershipService:
    """Invite, accept, leave, and remove, using the group and invitation repositories.

    The inviter must already be a member. Invites are emailed after they are
    saved, and acceptance verifies the user's email matches the invite before
    adding the user to the roster and marking it accepted.
    """
    def __init__(
        self,
        groupRepo: GroupRepository,
        inviteRepo: GroupInvitationRepository,
        userRepo: UserRepository,
        emailService: EmailService,
        templateFactory: GroupEmailTemplateFactory,
        inviteValidity: timedelta = timedelta(days=7),
    ):
        self._groupRepo = groupRepo
        self._inviteRepo = inviteRepo
        self._userRepo = userRepo
        self._emailService = emailService
        self._templateFactory = templateFactory
        self._inviteValidity = inviteValidity

    def inviteUser(self, groupId: int, email: str, inviterUserId: int) -> Invitation:
        """Save a pending invite and email it; retain the invite if delivery fails."""
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

        if "@ilstu.edu" not in invitation.inviteeEmail:
            raise ValueError("Invitations must go to an @ilstu.edu address")
        self._inviteRepo.save(invitation)

        group = self._groupRepo.findById(groupId)
        body = self._templateFactory.buildInvitationEmail(group.groupName, invitation.inviteToken)
        try:
            self._emailService.sendEmail(
                invitation.inviteeEmail,
                f"Invitation to {group.groupName}",
                body,
            )
        except MailDeliveryError as error:
            raise InvitationMailDeliveryError(invitation) from error

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

        user = self._userRepo.findById(userId)
        if user is None:
            raise LookupError("User not found")
        if user.email != invitation.inviteeEmail:
            raise PermissionError("Sign in with the invited email before joining")

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

    def removeMemberFromRoster(self, groupId: int, targetUserId: int, actorUserId: int) -> None:
        """Remove another member, after verifying the actor and target memberships."""
        if not self._isMember(groupId, actorUserId):
            raise PermissionError("Only group members can remove members")
        if targetUserId == actorUserId:
            raise ValueError("Leave the group instead of removing yourself")
        if not self._isMember(groupId, targetUserId):
            raise LookupError("User is not a member of this group")
        self._groupRepo.removeMember(groupId, targetUserId)

    def leaveGroup(self, userId: int, groupId: int) -> None:
        """Remove the caller from the group, or raise if they are not a member."""
        if not self._isMember(groupId, userId):
            raise LookupError("User is not a member of this group")
        self._groupRepo.removeMember(groupId, userId)

    def _isMember(self, groupId: int, userId: int) -> bool:
        return self._groupRepo.isMember(groupId, userId)

    def declineInvite(self, inviteToken: str) -> None:
        invitation = self._inviteRepo.findByToken(inviteToken)
        if invitation is None:
            raise LookupError("Invitation not found")
        if invitation.isExpired() is True:
            raise ValueError("Invitation has expired")
        if invitation.status != Invitation.PENDING:
            raise ValueError(f"Invitation has already been {invitation.status}")
        self._inviteRepo.save(
            Invitation(
                invitation.groupId,
                invitation.inviterUserId,
                invitation.inviteToken,
                invitation.inviteeEmail,
                Invitation.DECLINED,
                invitation.expiresAt,
            )
        )
