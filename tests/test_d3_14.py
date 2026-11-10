# Tests for D3-14: share my meetings by email

from datetime import datetime

from scheduler.application import buildApplication
from scheduler.controllers.meeting_controller import MeetingController
from scheduler.domain.scheduled_meeting import ScheduledMeeting
from scheduler.domain.time_slot import TimeSlot
from scheduler.infrastructure.duckdb_connection import DuckDBConnection
from scheduler.infrastructure.ics_exporter import IcsExporter
from scheduler.infrastructure.password_hasher import PasswordHasher
from scheduler.repositories.group_repository import GroupRepository
from scheduler.repositories.scheduled_meeting_repository import ScheduledMeetingRepository
from scheduler.repositories.user_repository import UserRepository
from scheduler.services.authentication_service import AuthenticationService
from scheduler.services.group_service import GroupService
from scheduler.services.meeting_retrieval_service import MeetingRetrievalService


class FakeEmailService:
    # Records every attachment email instead of sending it
    def __init__(self):
        self.sent = []

    def sendEmailWithAttachment(self, to, subject, body, filename, content):
        self.sent.append((to, subject, body, filename, content))


def makeUser(app, number):
    email = f"user{number}@ilstu.edu"
    app.userController.handleRegisterUser(
        {"email": email, "password": "secret12", "firstName": "User", "lastName": str(number)}
    )
    token = app.authController.handleLogin({"email": email, "password": "secret12"}).data["token"]
    return token, app.sessionManager.getSession(token).userId


def setup():
    # User 1 has two scheduled meetings and one cancelled one. User 2 has no meetings.
    app = buildApplication(DuckDBConnection(":memory:"), secretKey="test-secret", mailHost="console")
    token1, id1 = makeUser(app, 1)
    token2, id2 = makeUser(app, 2)
    groupRepo = GroupRepository(app.database)
    group = GroupService(groupRepo).createGroup(id1, "IT 426", "")

    slot = TimeSlot(datetime(2026, 11, 2, 15, 0), datetime(2026, 11, 2, 16, 0), "weekly")
    meetingRepo = ScheduledMeetingRepository(app.database)
    meetingRepo.save(ScheduledMeeting(None, group.groupId, "First meeting", [slot]))
    meetingRepo.save(ScheduledMeeting(None, group.groupId, "Second meeting", [slot]))
    cancelled = ScheduledMeeting(None, group.groupId, "Cancelled meeting", [slot])
    cancelled.cancelMeeting()
    meetingRepo.save(cancelled)

    # A controller that uses a fake email service so the attachment can be inspected
    fakeEmail = FakeEmailService()
    retrieval = MeetingRetrievalService(meetingRepo, fakeEmail, IcsExporter())
    authService = AuthenticationService(UserRepository(app.database), app.sessionManager, PasswordHasher())
    controller = MeetingController(retrieval, None, IcsExporter(), authService)
    return controller, fakeEmail, token1, token2


def test_share_attaches_only_scheduled_meetings():
    controller, fakeEmail, token1, _ = setup()
    r = controller.handleShareMeetings({"token": token1, "email": "coach@example.com"})
    assert r.status == "ok"
    assert r.data is None
    assert len(fakeEmail.sent) == 1
    to, subject, body, filename, content = fakeEmail.sent[0]
    assert to == "coach@example.com"
    assert subject == "Shared meeting schedule"
    assert body == "2 meetings are attached."
    assert filename == "meetings.ics"
    text = content.decode("utf-8")
    assert text.count("BEGIN:VCALENDAR") == 1
    assert text.count("BEGIN:VEVENT") == 2
    assert "SUMMARY:First meeting" in text
    assert "SUMMARY:Second meeting" in text
    assert "Cancelled meeting" not in text


def test_bad_address_is_invalid_and_sends_nothing():
    controller, fakeEmail, token1, _ = setup()
    r = controller.handleShareMeetings({"token": token1, "email": "not-an-email"})
    assert r.status == "invalid"
    assert fakeEmail.sent == []


def test_no_meetings_is_invalid():
    controller, fakeEmail, _, token2 = setup()
    r = controller.handleShareMeetings({"token": token2, "email": "coach@example.com"})
    assert r.status == "invalid"
    assert r.message == "There is no active meeting to share"
    assert fakeEmail.sent == []


def test_any_domain_is_allowed():
    controller, fakeEmail, token1, _ = setup()
    r = controller.handleShareMeetings({"token": token1, "email": "someone@gmail.com"})
    assert r.status == "ok"


def test_no_token_is_unauthenticated():
    controller, fakeEmail, token1, _ = setup()
    assert controller.handleShareMeetings({"email": "coach@example.com"}).status == "unauthenticated"