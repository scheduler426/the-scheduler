# Tests for D3-11: send an email reminder to members

from datetime import datetime, timedelta

from scheduler.application import buildApplication
from scheduler.domain.meeting_poll import MeetingPoll
from scheduler.domain.time_slot import TimeSlot
from scheduler.infrastructure.duckdb_connection import DuckDBConnection
from scheduler.repositories.group_repository import GroupRepository
from scheduler.repositories.meeting_poll_repository import MeetingPollRepository
from scheduler.services.group_service import GroupService


def makeUser(app, number):
    email = f"user{number}@ilstu.edu"
    app.userController.handleRegisterUser(
        {"email": email, "password": "secret12", "firstName": "User", "lastName": str(number)}
    )
    token = app.authController.handleLogin({"email": email, "password": "secret12"}).data["token"]
    return token, app.sessionManager.getSession(token).userId


def setup():
    # Users 1 and 2 are members, user 3 is an outsider
    app = buildApplication(DuckDBConnection(":memory:"), secretKey="test-secret", mailHost="console")
    token1, id1 = makeUser(app, 1)
    token2, id2 = makeUser(app, 2)
    outsiderToken, _ = makeUser(app, 3)
    groupRepo = GroupRepository(app.database)
    group = GroupService(groupRepo).createGroup(id1, "IT 426", "")
    groupRepo.addMember(group.groupId, id2)
    return app, group.groupId, token1, id1, id2, outsiderToken


def test_member_sends_reminder(capsys):
    app, groupId, token1, id1, id2, _ = setup()
    capsys.readouterr()  # drop the welcome emails
    r = app.notificationController.handleSendManualReminder(
        {"token": token1, "groupId": groupId, "targetUserIds": [id1, id2], "message": "Vote today"}
    )
    assert r.status == "ok"
    out = capsys.readouterr().out
    assert "Subject: Reminder from IT 426" in out
    assert "Vote today" in out


def test_non_member_is_forbidden_and_sends_nothing(capsys):
    app, groupId, token1, id1, id2, outsiderToken = setup()
    capsys.readouterr()
    r = app.notificationController.handleSendManualReminder(
        {"token": outsiderToken, "groupId": groupId, "targetUserIds": [id1], "message": "Hi"}
    )
    assert r.status == "forbidden"
    assert capsys.readouterr().out == ""


def test_blank_message_is_invalid():
    app, groupId, token1, id1, id2, _ = setup()
    r = app.notificationController.handleSendManualReminder(
        {"token": token1, "groupId": groupId, "targetUserIds": [id2], "message": " "}
    )
    assert r.status == "invalid"


def test_unknown_group_is_not_found():
    app, groupId, token1, id1, id2, _ = setup()
    r = app.notificationController.handleSendManualReminder(
        {"token": token1, "groupId": 9999, "targetUserIds": [id2], "message": "Hi"}
    )
    assert r.status == "notFound"


def test_remind_the_unvoted_members(capsys):
    app, groupId, token1, id1, id2, _ = setup()
    suggestions = {1: TimeSlot(datetime(2026, 11, 2, 15, 0), datetime(2026, 11, 2, 16, 0), "weekly")}
    MeetingPollRepository(app.database).save(
        MeetingPoll(None, groupId, datetime.now() + timedelta(days=2), True, suggestions)
    )
    status = app.voteController.handleGetPollStatus({"token": token1, "groupId": groupId})
    unvotedIds = [u["userId"] for u in status.data["unvotedMembers"]]
    assert unvotedIds  # nobody has voted yet
    capsys.readouterr()
    r = app.notificationController.handleSendManualReminder(
        {"token": token1, "groupId": groupId, "targetUserIds": unvotedIds, "message": "Please vote"}
    )
    assert r.status == "ok"
    assert "Reminder from IT 426" in capsys.readouterr().out


def test_no_token_is_unauthenticated():
    app, groupId, token1, id1, id2, _ = setup()
    r = app.notificationController.handleSendManualReminder(
        {"groupId": groupId, "targetUserIds": [id1], "message": "Hi"}
    )
    assert r.status == "unauthenticated"