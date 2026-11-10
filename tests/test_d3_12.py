# Tests for D3-12: cancel a meeting

from datetime import datetime

from scheduler.application import buildApplication
from scheduler.controllers.scheduling_controller import SchedulingController
from scheduler.domain.scheduled_meeting import ScheduledMeeting
from scheduler.domain.time_slot import TimeSlot
from scheduler.infrastructure.duckdb_connection import DuckDBConnection
from scheduler.infrastructure.email_service import MailDeliveryError
from scheduler.infrastructure.group_email_template_factory import GroupEmailTemplateFactory
from scheduler.infrastructure.password_hasher import PasswordHasher
from scheduler.repositories.group_repository import GroupRepository
from scheduler.repositories.meeting_poll_repository import MeetingPollRepository
from scheduler.repositories.scheduled_meeting_repository import ScheduledMeetingRepository
from scheduler.repositories.user_repository import UserRepository
from scheduler.services.authentication_service import AuthenticationService
from scheduler.services.group_notification_service import GroupNotificationService
from scheduler.services.group_service import GroupService
from scheduler.services.meeting_finalization_service import MeetingFinalizationService


class BrokenEmailService:
    # Every send fails, like a bad mail host
    def sendBulkEmail(self, toList, subject, body):
        raise MailDeliveryError("SMTP host is not reachable")


def makeUser(app, number):
    email = f"user{number}@ilstu.edu"
    app.userController.handleRegisterUser(
        {"email": email, "password": "secret12", "firstName": "User", "lastName": str(number)}
    )
    token = app.authController.handleLogin({"email": email, "password": "secret12"}).data["token"]
    return token, app.sessionManager.getSession(token).userId


def setup():
    # Users 1 and 2 are in the group, and the group has one scheduled meeting
    app = buildApplication(DuckDBConnection(":memory:"), secretKey="test-secret", mailHost="console")
    token1, id1 = makeUser(app, 1)
    token2, id2 = makeUser(app, 2)
    groupRepo = GroupRepository(app.database)
    group = GroupService(groupRepo).createGroup(id1, "IT 426", "")
    groupRepo.addMember(group.groupId, id2)
    slot = TimeSlot(datetime(2026, 11, 2, 15, 0), datetime(2026, 11, 2, 16, 0), "weekly")
    meetingRepo = ScheduledMeetingRepository(app.database)
    meetingId = meetingRepo.save(ScheduledMeeting(None, group.groupId, "IT 426 weekly", [slot]))
    return app, groupRepo, meetingRepo, token1, id1, id2, meetingId


def storedStatus(meetingRepo, userId, meetingId):
    # findAllByUserId includes cancelled meetings
    return next(m.status for m in meetingRepo.findAllByUserId(userId) if m.meetingId == meetingId)


def test_cancel_marks_cancelled_and_emails_the_other_member(capsys):
    app, groupRepo, meetingRepo, token1, id1, id2, meetingId = setup()
    capsys.readouterr()  # drop the welcome emails
    r = app.schedulingController.handleCancelMeeting({"token": token1, "meetingId": meetingId})
    assert r.status == "ok"
    assert storedStatus(meetingRepo, id1, meetingId) == "cancelled"
    out = capsys.readouterr().out
    assert out.count("To: ") == 1
    assert "To: user2@ilstu.edu" in out
    assert "To: user1@ilstu.edu" not in out
    assert '"IT 426 weekly" has been cancelled.' in out


def test_cancel_again_is_not_found():
    app, groupRepo, meetingRepo, token1, id1, id2, meetingId = setup()
    app.schedulingController.handleCancelMeeting({"token": token1, "meetingId": meetingId})
    r = app.schedulingController.handleCancelMeeting({"token": token1, "meetingId": meetingId})
    assert r.status == "notFound"


def test_cancelled_meeting_is_no_longer_listed():
    app, groupRepo, meetingRepo, token1, id1, id2, meetingId = setup()
    assert len(app.meetingController.handleGetMyMeetings({"token": token1}).data) == 1
    app.schedulingController.handleCancelMeeting({"token": token1, "meetingId": meetingId})
    assert app.meetingController.handleGetMyMeetings({"token": token1}).data == []


def test_broken_mail_still_cancels_and_returns_mail_failed():
    app, groupRepo, meetingRepo, token1, id1, id2, meetingId = setup()
    notifier = GroupNotificationService(BrokenEmailService(), groupRepo, GroupEmailTemplateFactory())
    finalization = MeetingFinalizationService(meetingRepo, MeetingPollRepository(app.database), notifier, groupRepo)
    authService = AuthenticationService(UserRepository(app.database), app.sessionManager, PasswordHasher())
    controller = SchedulingController(app.schedulingController._suggestionService, finalization, authService)
    r = controller.handleCancelMeeting({"token": token1, "meetingId": meetingId})
    assert r.status == "mailFailed"
    assert storedStatus(meetingRepo, id1, meetingId) == "cancelled"


def test_non_member_cannot_cancel():
    app, groupRepo, meetingRepo, token1, id1, id2, meetingId = setup()
    outsiderToken, _ = makeUser(app, 3)
    r = app.schedulingController.handleCancelMeeting({"token": outsiderToken, "meetingId": meetingId})
    assert r.status == "notFound"
    assert storedStatus(meetingRepo, id1, meetingId) == "scheduled"


def test_no_token_is_unauthenticated():
    app, groupRepo, meetingRepo, token1, id1, id2, meetingId = setup()
    assert app.schedulingController.handleCancelMeeting({"meetingId": meetingId}).status == "unauthenticated"