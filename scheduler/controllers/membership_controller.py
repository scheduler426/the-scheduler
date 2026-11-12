"""Handles authenticated requests to manage group membership."""

from __future__ import annotations

from scheduler.infrastructure.email_service import MailDeliveryError
from scheduler.controllers.response import Response, respond
from scheduler.domain.invitation import Invitation
from scheduler.services.authentication_service import AuthenticationService
from scheduler.services.group_membership_service import (
    GroupMembershipService,
    InvitationMailDeliveryError,
)


class MembershipController:
    """Turns group membership requests into service calls and Responses."""

    def __init__(self, membershipService: GroupMembershipService, authService: AuthenticationService):
        self._membershipService = membershipService
        self._authService = authService

    def handleSendInvite(self, request: dict) -> Response:
        return respond(lambda: self._sendInvite(request))

    def handleAcceptInvite(self, httpRequest: dict) -> Response:
        return respond(lambda: self._acceptInvite(httpRequest))

    def handleRemoveMember(self, request: dict) -> Response:
        return respond(lambda: self._removeMember(request))

    def handleLeaveGroup(self, request: dict) -> Response:
        return respond(lambda: self._leaveGroup(request))

    def handleDeclineInvite(self, request: dict) -> Response:
        return respond(lambda: self._declineInvite(request))

    def _sendInvite(self, request: dict) -> list[dict]:
        session = self._authService.requireSession(request.get("token"))
        groupId = self._required(request, "groupId")
        emails = request.get("emails")
        if not isinstance(emails, list) or not emails:
            raise ValueError("emails must be a non-empty list")
        if any(
            not isinstance(email, str) or not email.strip().lower().endswith("@ilstu.edu")
            for email in emails
        ):
            raise ValueError("Invitations must go to @ilstu.edu addresses")

        invitations: list[dict] = []
        savedTokens: list[str] = []
        for email in emails:
            try:
                invitation = self._membershipService.inviteUser(groupId, email, session.userId)
            except InvitationMailDeliveryError as error:
                savedTokens.append(error.inviteToken)
                raise MailDeliveryError(
                    f"Invitations saved with tokens {', '.join(savedTokens)}; "
                    f"email was not sent to {error.inviteeEmail}"
                ) from error
            savedTokens.append(invitation.inviteToken)
            invitations.append(self._invitationData(invitation))
        return invitations

    def _acceptInvite(self, httpRequest: dict) -> None:
        session = self._authService.requireSession(httpRequest.get("token"))
        inviteToken = self._required(httpRequest, "inviteToken")
        self._membershipService.processInviteLink(inviteToken, session.userId)

    def _removeMember(self, request: dict) -> None:
        session = self._authService.requireSession(request.get("token"))
        groupId = self._required(request, "groupId")
        targetUserId = self._required(request, "targetUserId")
        self._membershipService.removeMemberFromRoster(groupId, targetUserId, session.userId)

    def _leaveGroup(self, request: dict) -> None:
        session = self._authService.requireSession(request.get("token"))
        groupId = self._required(request, "groupId")
        self._membershipService.leaveGroup(session.userId, groupId)

    def _declineInvite(self, request: dict) -> None:
        inviteToken = self._required(request, "inviteToken")
        self._membershipService.declineInvite(inviteToken)

    @staticmethod
    def _required(request: dict, key: str):
        if request.get(key) is None:
            raise ValueError(f"{key} is required")
        return request[key]

    @staticmethod
    def _invitationData(invitation: Invitation) -> dict:
        return {
            "inviteToken": invitation.inviteToken,
            "groupId": invitation.groupId,
            "inviteeEmail": invitation.inviteeEmail,
            "status": invitation.status,
            "expiresAt": invitation.expiresAt.isoformat(),
        }
