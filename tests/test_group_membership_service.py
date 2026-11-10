"""Invitation email delivery through GroupMembershipService."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from scheduler.domain.group import Group
from scheduler.domain.invitation import Invitation
from scheduler.domain.user import User
from scheduler.infrastructure.duckdb_connection import DuckDBConnection
from scheduler.infrastructure.email_service import MailDeliveryError
from scheduler.infrastructure.group_email_template_factory import GroupEmailTemplateFactory
from scheduler.repositories.group_invitation_repository import GroupInvitationRepository
from scheduler.repositories.group_repository import GroupRepository
from scheduler.repositories.user_repository import UserRepository
from scheduler.services.group_membership_service import GroupMembershipService


class FailingEmailService:
    def __init__(self):
        self.sent = []

    def sendEmail(self, to: str, subject: str, body: str) -> None:
        self.sent.append((to, subject, body))
        raise MailDeliveryError("SMTP unavailable")


def test_inviteUserKeepsSavedInvitationWhenEmailFails():
    db = DuckDBConnection(":memory:")
    groupRepo = GroupRepository(db)
    groupId = groupRepo.save(Group(None, "IT 426"))
    groupRepo.addMember(groupId, 17)
    inviteRepo = GroupInvitationRepository(db)
    userRepo = UserRepository(db)
    emailService = FailingEmailService()
    service = GroupMembershipService(
        groupRepo,
        inviteRepo,
        userRepo,
        emailService,
        GroupEmailTemplateFactory({"invitation": "Join {groupName} with token {token}"}),
    )

    with pytest.raises(MailDeliveryError, match=r"Invitation .+ was saved but the email was not sent") as error:
        service.inviteUser(groupId, "student@ilstu.edu", 17)

    token = emailService.sent[0][2].split("token ", 1)[1]
    assert str(error.value) == f"Invitation {token} was saved but the email was not sent"
    assert emailService.sent[0][:2] == ("student@ilstu.edu", "Invitation to IT 426")
    assert db.sql(
        "SELECT inviteeEmail, status, inviteToken FROM groupInvitations WHERE inviteToken = ?", [token]
    ).fetchone() == ("student@ilstu.edu", "pending", token)
    db.close()


def makeInvitationService(db):
    groupRepo = GroupRepository(db)
    inviteRepo = GroupInvitationRepository(db)
    userRepo = UserRepository(db)
    return (
        groupRepo,
        inviteRepo,
        userRepo,
        GroupMembershipService(
            groupRepo,
            inviteRepo,
            userRepo,
            FailingEmailService(),
            GroupEmailTemplateFactory({"invitation": "Join {groupName}: {token}"}),
        ),
    )


def test_processInviteLinkRejectsDifferentUserEmailBeforeJoining():
    db = DuckDBConnection(":memory:")
    groupRepo, inviteRepo, userRepo, service = makeInvitationService(db)
    groupId = groupRepo.save(Group(None, "IT 426"))
    userId = userRepo.save(User(None, "other@ilstu.edu", "hash", "Ada", "Lovelace"))
    token = "invite-token"
    inviteRepo.save(
        Invitation(groupId, userId, token, "invited@ilstu.edu", Invitation.PENDING, datetime.now() + timedelta(days=1))
    )

    with pytest.raises(PermissionError, match="Sign in with the invited email before joining"):
        service.processInviteLink(token, userId)

    assert not groupRepo.isMember(groupId, userId)
    assert inviteRepo.findByToken(token).status == Invitation.PENDING
    db.close()


def test_processInviteLinkAcceptsMatchingUserEmail():
    db = DuckDBConnection(":memory:")
    groupRepo, inviteRepo, userRepo, service = makeInvitationService(db)
    groupId = groupRepo.save(Group(None, "IT 426"))
    userId = userRepo.save(User(None, "invited@ilstu.edu", "hash", "Ada", "Lovelace"))
    token = "invite-token"
    inviteRepo.save(
        Invitation(groupId, userId, token, "invited@ilstu.edu", Invitation.PENDING, datetime.now() + timedelta(days=1))
    )

    service.processInviteLink(token, userId)

    assert groupRepo.isMember(groupId, userId)
    assert inviteRepo.findByToken(token).status == Invitation.ACCEPTED
    db.close()


def test_removeMemberFromRosterRequiresActorMembership():
    db = DuckDBConnection(":memory:")
    groupRepo, _, _, service = makeInvitationService(db)
    groupId = groupRepo.save(Group(None, "IT 426"))
    groupRepo.addMember(groupId, 17)

    with pytest.raises(PermissionError, match="Only group members can remove members"):
        service.removeMemberFromRoster(groupId, 17, 99)

    assert groupRepo.isMember(groupId, 17)
    db.close()


def test_removeMemberFromRosterRejectsSelfRemoval():
    db = DuckDBConnection(":memory:")
    groupRepo, _, _, service = makeInvitationService(db)
    groupId = groupRepo.save(Group(None, "IT 426"))
    groupRepo.addMember(groupId, 17)

    with pytest.raises(ValueError, match="Leave the group instead of removing yourself"):
        service.removeMemberFromRoster(groupId, 17, 17)

    assert groupRepo.isMember(groupId, 17)
    db.close()


def test_removeMemberFromRosterRequiresTargetMembership():
    db = DuckDBConnection(":memory:")
    groupRepo, _, _, service = makeInvitationService(db)
    groupId = groupRepo.save(Group(None, "IT 426"))
    groupRepo.addMember(groupId, 17)

    with pytest.raises(LookupError, match="User is not a member of this group"):
        service.removeMemberFromRoster(groupId, 99, 17)

    db.close()


def test_removeMemberFromRosterRemovesAnotherMemberAndLeaveGroupStillWorks():
    db = DuckDBConnection(":memory:")
    groupRepo, _, _, service = makeInvitationService(db)
    groupId = groupRepo.save(Group(None, "IT 426"))
    groupRepo.addMember(groupId, 17)
    groupRepo.addMember(groupId, 18)

    service.removeMemberFromRoster(groupId, 18, 17)
    assert not groupRepo.isMember(groupId, 18)

    service.leaveGroup(17, groupId)
    assert not groupRepo.isMember(groupId, 17)
    db.close()
