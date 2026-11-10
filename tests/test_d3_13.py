# Tests for D3-13: set a meeting reminder

from datetime import datetime, timedelta

from scheduler.application import buildApplication
from scheduler.domain.scheduled_meeting import ScheduledMeeting
from scheduler.domain.time_slot import TimeSlot
from scheduler.infrastructure.duckdb_connection import DuckDBConnection
from scheduler.repositories.group_repository import GroupRepository
from scheduler.repositories.notification_repository import NotificationRepository
from scheduler.repositories.scheduled_meeting_repository import ScheduledMeetingRepository
from scheduler.services.group_service import GroupService


def makeUser(app, number):
    email = f"user{number}@ilstu.edu"
    app.userController.handleRegisterUser(
        {"email": email, "password": "secret12", "firstName": "User", "lastName": str(number)}
    )
    token = app.authController.handleLogin({"email": email, "password": "secret12"}).data["token"]
    return token, app.sessionManager.getSession(token).userId


def setup():
    # User 1 is in a group with one scheduled meeting and one cancelled meeting
    app = buildApplication(DuckDBConnection(":memory:"), secretKey="test-secret", mailHost="console")
    token1, id1 = makeUser(app, 1)
    groupRepo = GroupRepository(app.database)
    group = GroupService(groupRepo).createGroup(id1, "IT 426", "")
    slot = TimeSlot(datetime(2026, 11, 16, 15, 0), datetime(2026, 11, 16, 16, 0), "weekly")
    meetingRepo = ScheduledMeetingRepository(app.database)
    scheduledId = meetingRepo.save(ScheduledMeeting(None, group.groupId, "IT 426 weekly", [slot]))
    cancelled = ScheduledMeeting(None, group.groupId, "Cancelled one", [slot])
    cancelled.cancelMeeting()
    cancelledId = meetingRepo.save(cancelled)
    return app, token1, id1, scheduledId, cancelledId


def statuses(app):
    rows = app.database.sql("SELECT status FROM notifications ORDER BY notificationId").fetchall()
    return [row[0] for row in rows]


def test_set_reminder_is_ok():
    app, token1, id1, scheduledId, _ = setup()
    sendAt = datetime.now() + timedelta(minutes=1)
    r = app.notificationController.handleSetMeetingReminder(
        {"token": token1, "meetingId": scheduledId, "sendAt": sendAt}
    )
    assert r.status == "ok"
    assert r.data["meetingId"] == scheduledId
    assert r.data["sendAt"] == sendAt
    assert statuses(app) == ["scheduled"]


def test_delivery_waits_for_the_time_then_sends(capsys):
    app, token1, id1, scheduledId, _ = setup()
    sendAt = datetime.now() + timedelta(minutes=1)
    app.notificationController.handleSetMeetingReminder(
        {"token": token1, "meetingId": scheduledId, "sendAt": sendAt}
    )
    capsys.readouterr()  # drop the welcome email

    # Before the time: nothing is sent
    app.groupNotificationService.deliverDueReminders(sendAt - timedelta(seconds=30))
    assert capsys.readouterr().out == ""
    assert statuses(app) == ["scheduled"]

    # After the time: one reminder goes out and the row is sent
    app.groupNotificationService.deliverDueReminders(sendAt + timedelta(seconds=1))
    out = capsys.readouterr().out
    assert out.count("Subject: Meeting reminder") == 1
    assert "To: user1@ilstu.edu" in out
    assert "IT 426 weekly" in out
    assert statuses(app) == ["sent"]

    # Running again sends nothing more
    app.groupNotificationService.deliverDueReminders(sendAt + timedelta(minutes=5))
    assert capsys.readouterr().out == ""


def test_reminders_off_marks_sent_without_email(capsys):
    app, token1, id1, scheduledId, _ = setup()
    sendAt = datetime.now() + timedelta(minutes=1)
    app.notificationController.handleSetMeetingReminder(
        {"token": token1, "meetingId": scheduledId, "sendAt": sendAt}
    )
    app.database.sql("UPDATE users SET allowEmailReminders = FALSE WHERE userId = ?", [id1])
    capsys.readouterr()
    app.groupNotificationService.deliverDueReminders(sendAt + timedelta(seconds=1))
    assert capsys.readouterr().out == ""
    assert statuses(app) == ["sent"]


def test_past_time_is_invalid():
    app, token1, id1, scheduledId, _ = setup()
    r = app.notificationController.handleSetMeetingReminder(
        {"token": token1, "meetingId": scheduledId, "sendAt": datetime.now() - timedelta(minutes=1)}
    )
    assert r.status == "invalid"
    assert statuses(app) == []


def test_cancelled_meeting_is_not_found():
    app, token1, id1, _, cancelledId = setup()
    r = app.notificationController.handleSetMeetingReminder(
        {"token": token1, "meetingId": cancelledId, "sendAt": datetime.now() + timedelta(minutes=1)}
    )
    assert r.status == "notFound"


def test_several_reminders_for_one_meeting_are_allowed():
    app, token1, id1, scheduledId, _ = setup()
    for minutes in (1, 2):
        r = app.notificationController.handleSetMeetingReminder(
            {"token": token1, "meetingId": scheduledId, "sendAt": datetime.now() + timedelta(minutes=minutes)}
        )
        assert r.status == "ok"
    assert statuses(app) == ["scheduled", "scheduled"]


def test_no_token_is_unauthenticated():
    app, token1, id1, scheduledId, _ = setup()
    r = app.notificationController.handleSetMeetingReminder(
        {"meetingId": scheduledId, "sendAt": datetime.now() + timedelta(minutes=1)}
    )
    assert r.status == "unauthenticated"