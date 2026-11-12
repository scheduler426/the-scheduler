"""Batch invitation requests through MembershipController."""

from __future__ import annotations

import pytest

from scheduler.application import buildApplication
from scheduler.infrastructure.duckdb_connection import DuckDBConnection
from scheduler.infrastructure.email_service import MailDeliveryError


@pytest.fixture
def groupApp():
    app = buildApplication(DuckDBConnection(":memory:"), "test-secret", mailHost="console")
    registered = app.userController.handleRegisterUser(
        {"email": "group.member@ilstu.edu", "password": "secret12", "firstName": "Group", "lastName": "Member"}
    )
    token = app.sessionManager.createSession(registered.data["userId"]).token
    group = app.groupController.handleCreateGroup({"token": token, "name": "IT 426"})
    yield app, token, group.data["groupId"]
    app.close()


def test_handleSendInviteValidatesAllAddressesBeforeSaving(groupApp):
    app, token, groupId = groupApp

    response = app.membershipController.handleSendInvite(
        {"token": token, "groupId": groupId, "emails": ["first@ilstu.edu", "person@example.com"]}
    )

    assert response.status == "invalid"
    assert app.database.sql("SELECT count(*) FROM groupInvitations").fetchone()[0] == 0


def test_handleSendInviteReturnsInvitationData(groupApp):
    app, token, groupId = groupApp

    response = app.membershipController.handleSendInvite(
        {"token": token, "groupId": groupId, "emails": ["first@ilstu.edu", "second@ilstu.edu"]}
    )

    assert response.status == "ok"
    assert len(response.data) == 2
    assert all(
        set(invitation) == {"inviteToken", "groupId", "inviteeEmail", "status", "expiresAt"}
        and invitation["groupId"] == groupId
        and invitation["status"] == "pending"
        for invitation in response.data
    )


def test_handleSendInviteReportsSavedTokensOnPartialMailFailure(groupApp, monkeypatch):
    app, token, groupId = groupApp
    sent = []

    def sendEmail(to: str, subject: str, body: str) -> None:
        sent.append(to)
        if to == "second@ilstu.edu":
            raise MailDeliveryError("SMTP unavailable")

    monkeypatch.setattr(app.emailService, "sendEmail", sendEmail)

    response = app.membershipController.handleSendInvite(
        {
            "token": token,
            "groupId": groupId,
            "emails": ["first@ilstu.edu", "second@ilstu.edu", "third@ilstu.edu"],
        }
    )

    tokens = [
        row[0]
        for row in app.database.sql(
            "SELECT inviteToken FROM groupInvitations ORDER BY inviteeEmail"
        ).fetchall()
    ]
    assert response.status == "mailFailed"
    assert "second@ilstu.edu" in response.message
    assert all(inviteToken in response.message for inviteToken in tokens)
    assert len(tokens) == 2
    assert sent == ["first@ilstu.edu", "second@ilstu.edu"]


@pytest.mark.parametrize("emails", [None, [], "one@ilstu.edu"])
def test_handleSendInviteRequiresNonEmptyEmailList(groupApp, emails):
    app, token, groupId = groupApp

    response = app.membershipController.handleSendInvite(
        {"token": token, "groupId": groupId, "emails": emails}
    )

    assert response.status == "invalid"
    assert app.database.sql("SELECT count(*) FROM groupInvitations").fetchone()[0] == 0


def test_handleAcceptInviteAddsInvitedUser(groupApp):
    app, senderToken, groupId = groupApp
    registered = app.userController.handleRegisterUser(
        {"email": "invitee@ilstu.edu", "password": "secret12", "firstName": "Invitee", "lastName": "Student"}
    )
    inviteeToken = app.sessionManager.createSession(registered.data["userId"]).token
    invitation = app.membershipController.handleSendInvite(
        {"token": senderToken, "groupId": groupId, "emails": ["invitee@ilstu.edu"]}
    ).data[0]

    response = app.membershipController.handleAcceptInvite(
        {"token": inviteeToken, "inviteToken": invitation["inviteToken"]}
    )

    assert response.status == "ok" and response.data is None
    assert app.database.sql(
        "SELECT 1 FROM groupRoster WHERE groupId = ? AND userId = ?",
        [groupId, registered.data["userId"]],
    ).fetchone() == (1,)


def test_handleRemoveMemberUsesAuthenticatedActor(groupApp):
    app, token, groupId = groupApp
    registered = app.userController.handleRegisterUser(
        {"email": "member@ilstu.edu", "password": "secret12", "firstName": "Group", "lastName": "Member"}
    )
    targetUserId = registered.data["userId"]
    app.database.sql("INSERT INTO groupRoster (groupId, userId) VALUES (?, ?)", [groupId, targetUserId])

    response = app.membershipController.handleRemoveMember(
        {"token": token, "groupId": groupId, "targetUserId": targetUserId}
    )

    assert response.status == "ok" and response.data is None
    assert app.database.sql(
        "SELECT 1 FROM groupRoster WHERE groupId = ? AND userId = ?", [groupId, targetUserId]
    ).fetchone() is None


def test_handleLeaveGroupRemovesAuthenticatedUser(groupApp):
    app, token, groupId = groupApp
    userId = app.database.sql("SELECT userId FROM users WHERE email = ?", ["group.member@ilstu.edu"]).fetchone()[0]

    response = app.membershipController.handleLeaveGroup({"token": token, "groupId": groupId})

    assert response.status == "ok" and response.data is None
    assert app.database.sql(
        "SELECT 1 FROM groupRoster WHERE groupId = ? AND userId = ?", [groupId, userId]
    ).fetchone() is None


def test_handleDeclineInviteDoesNotRequireSession(groupApp):
    app, token, groupId = groupApp
    invitation = app.membershipController.handleSendInvite(
        {"token": token, "groupId": groupId, "emails": ["invitee@ilstu.edu"]}
    ).data[0]

    response = app.membershipController.handleDeclineInvite({"inviteToken": invitation["inviteToken"]})

    assert response.status == "ok" and response.data is None
    assert app.database.sql(
        "SELECT status FROM groupInvitations WHERE inviteToken = ?", [invitation["inviteToken"]]
    ).fetchone() == ("declined",)


def test_handleDeclineInviteRequiresToken(groupApp):
    app, _, _ = groupApp

    response = app.membershipController.handleDeclineInvite({})

    assert response.status == "invalid"
    assert response.message == "inviteToken is required"
