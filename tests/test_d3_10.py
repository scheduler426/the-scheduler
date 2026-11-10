# Tests for D3-10: report a scheduling conflict

from datetime import datetime

from scheduler.application import buildApplication
from scheduler.controllers.meeting_controller import MeetingController
from scheduler.domain.scheduled_meeting import ScheduledMeeting
from scheduler.domain.time_slot import TimeSlot
from scheduler.infrastructure.duckdb_connection import DuckDBConnection
from scheduler.infrastructure.ics_exporter import IcsExporter
from scheduler.infrastructure.scheduling_email_template_factory import SchedulingEmailTemplateFactory
from scheduler.repositories.group_repository import GroupRepository
from scheduler.repositories.scheduled_meeting_repository import ScheduledMeetingRepository
from scheduler.services.conflict_reporting_service import ConflictReportingService
from scheduler.services.group_service import GroupService
from scheduler.services.meeting_retrieval_service import MeetingRetrievalService


class FakeEmailService:
    # Records every bulk email instead of sending it
    def __init__(self):
        self.sent = []

    def sendBulkEmail(self, toList, subject, body):
        self.sent.append((list(toList), subject, body))


def makeUser(app, email, firstName, lastName):
    app.userController.handleRegisterUser(
        {"email": email, "password": "secret12", "firstName": firstName, "lastName": lastName}
    )
    token = app.authController.handleLogin({"email": email, "password": "secret12"}).data["token"]
    return token, app.sessionManager.getSession(token).userId


def setup():
    # Ada and Bo are both in the group, both with reminders on
    app = buildApplication(DuckDBConnection(":memory:"), secretKey="test-secret", mailHost="console")
    adaToken, adaId = makeUser(app, "ada@ilstu.edu", "Ada", "Lovelace")
    boToken, boId = makeUser(app, "bo@ilstu.edu", "Bo", "Test")
    groupRepo = GroupRepository(app.database)
    group = GroupService(groupRepo).createGroup(adaId, "IT 426", "")
    groupRepo.addMember(group.groupId, boId)

    slot = TimeSlot(datetime(2026, 11, 2, 15, 0), datetime(2026, 11, 2, 16, 0), "weekly")
    meetingRepo = ScheduledMeetingRepository(app.database)
    scheduledId = meetingRepo.save(ScheduledMeeting(None, group.groupId, "IT 426 weekly", [slot]))
    cancelled = ScheduledMeeting(None, group.groupId, "Cancelled one", [slot])
    cancelled.cancelMeeting()
    cancelledId = meetingRepo.save(cancelled)

    # Build a controller that uses a fake email service so we can see what was sent
    fakeEmail = FakeEmailService()
    retrieval = MeetingRetrievalService(meetingRepo)
    conflictService = ConflictReportingService(fakeEmail, SchedulingEmailTemplateFactory(), retrieval, groupRepo)
    controller = MeetingController(retrieval, conflictService, IcsExporter(), app.availabilityController and app.authController._authService)
    return controller, fakeEmail, adaToken, scheduledId, cancelledId


def test_conflict_emails_only_the_other_member():
    controller, fakeEmail, adaToken, scheduledId, _ = setup()
    r = controller.handleReportConflict({"token": adaToken, "meetingId": scheduledId, "reason": "Exam that day"})
    assert r.status == "ok"
    assert r.data == {"meetingId": scheduledId, "reason": "Exam that day"}
    assert len(fakeEmail.sent) == 1
    toList, subject, body = fakeEmail.sent[0]
    assert toList == ["bo@ilstu.edu"]
    assert subject == "Schedule conflict reported"
    assert "IT 426 weekly" in body
    assert "Ada Lovelace" in body
    assert "Exam that day" in body


def test_blank_reason_is_invalid_and_sends_nothing():
    controller, fakeEmail, adaToken, scheduledId, _ = setup()
    r = controller.handleReportConflict({"token": adaToken, "meetingId": scheduledId, "reason": "   "})
    assert r.status == "invalid"
    assert fakeEmail.sent == []


def test_cancelled_meeting_is_not_found():
    controller, fakeEmail, adaToken, _, cancelledId = setup()
    r = controller.handleReportConflict({"token": adaToken, "meetingId": cancelledId, "reason": "Exam"})
    assert r.status == "notFound"
    assert fakeEmail.sent == []


def test_no_token_is_unauthenticated():
    controller, fakeEmail, adaToken, scheduledId, _ = setup()
    assert controller.handleReportConflict({"meetingId": scheduledId, "reason": "x"}).status == "unauthenticated"