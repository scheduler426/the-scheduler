# Tests for D3-6: group email reminder service

import pytest

from scheduler.application import buildApplication
from scheduler.infrastructure.duckdb_connection import DuckDBConnection
from scheduler.infrastructure.group_email_template_factory import GroupEmailTemplateFactory
from scheduler.repositories.group_repository import GroupRepository
from scheduler.repositories.user_repository import UserRepository
from scheduler.services.group_notification_service import GroupNotificationService
from scheduler.services.group_service import GroupService


class FakeEmailService:
    # Records every bulk email instead of sending it
    def __init__(self):
        self.sent = []

    def sendBulkEmail(self, toList, subject, body):
        self.sent.append((list(toList), subject, body))


def makeUser(app, email, firstName):
    app.userController.handleRegisterUser(
        {"email": email, "password": "secret12", "firstName": firstName, "lastName": "Test"}
    )
    token = app.authController.handleLogin({"email": email, "password": "secret12"}).data["token"]
    return app.sessionManager.getSession(token).userId


def setup():
    app = buildApplication(DuckDBConnection(":memory:"), secretKey="test-secret", mailHost="console")
    adaId = makeUser(app, "ada@ilstu.edu", "Ada")
    boId = makeUser(app, "bo@ilstu.edu", "Bo")

    # Bo turns reminders off
    userRepo = UserRepository(app.database)
    bo = userRepo.findById(boId) if hasattr(userRepo, "findById") else None
    app.database.sql("UPDATE users SET allowEmailReminders = FALSE WHERE userId = ?", [boId])

    groupRepo = GroupRepository(app.database)
    group = GroupService(groupRepo).createGroup(adaId, "IT 426", "")
    groupRepo.addMember(group.groupId, boId)

    fakeEmail = FakeEmailService()
    service = GroupNotificationService(fakeEmail, groupRepo, GroupEmailTemplateFactory())
    return service, fakeEmail, group, adaId, boId


def test_reminder_goes_only_to_members_with_reminders_on():
    service, fakeEmail, group, adaId, boId = setup()
    service.dispatchManualReminder(group.groupId, [adaId, boId, 999], "Tuesday at 3pm")
    assert len(fakeEmail.sent) == 1
    toList, subject, body = fakeEmail.sent[0]
    assert toList == ["ada@ilstu.edu"]
    assert subject == "Reminder from IT 426"
    assert "Tuesday at 3pm" in body
    assert "IT 426" in body


def test_blank_message_raises_and_sends_nothing():
    service, fakeEmail, group, adaId, boId = setup()
    with pytest.raises(ValueError):
        service.dispatchManualReminder(group.groupId, [adaId], "   ")
    assert fakeEmail.sent == []


def test_unknown_group_raises_lookup_error():
    service, fakeEmail, group, adaId, boId = setup()
    with pytest.raises(LookupError):
        service.dispatchManualReminder(9999, [adaId], "Hello")
    assert fakeEmail.sent == []


def test_nobody_left_sends_nothing():
    service, fakeEmail, group, adaId, boId = setup()
    service.dispatchManualReminder(group.groupId, [boId, 999], "Hello")
    assert fakeEmail.sent == []