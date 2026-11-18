# Tests for D3-9: export a meeting to .ics

from datetime import datetime

from scheduler.application import buildApplication
from scheduler.domain.scheduled_meeting import ScheduledMeeting
from scheduler.domain.time_slot import TimeSlot
from scheduler.infrastructure.duckdb_connection import DuckDBConnection
from scheduler.infrastructure.ics_parser import IcsParser
from scheduler.repositories.group_repository import GroupRepository
from scheduler.repositories.scheduled_meeting_repository import ScheduledMeetingRepository
from scheduler.services.group_service import GroupService

START = datetime(2026, 11, 2, 15, 0)
END = datetime(2026, 11, 2, 16, 0)


def setup():
    # One member with a scheduled meeting (one weekly slot) and a cancelled meeting
    app = buildApplication(DuckDBConnection(":memory:"), secretKey="test-secret", mailHost="console")
    app.userController.handleRegisterUser(
        {"email": "ada@ilstu.edu", "password": "secret12", "firstName": "Ada", "lastName": "Lovelace"}
    )
    token = app.authController.handleLogin({"email": "ada@ilstu.edu", "password": "secret12"}).data["token"]
    userId = app.sessionManager.getSession(token).userId
    groupRepo = GroupRepository(app.database)
    group = GroupService(groupRepo).createGroup(userId, "IT 426", "")

    slot = TimeSlot(START, END, "weekly")
    meetingRepo = ScheduledMeetingRepository(app.database)
    scheduledId = meetingRepo.save(ScheduledMeeting(None, group.groupId, "IT 426 weekly", [slot]))
    cancelled = ScheduledMeeting(None, group.groupId, "Cancelled one", [slot])
    cancelled.cancelMeeting()
    cancelledId = meetingRepo.save(cancelled)
    return app, token, scheduledId, cancelledId


def test_export_scheduled_meeting():
    app, token, scheduledId, _ = setup()
    r = app.meetingController.handleExportIcs({"token": token, "meetingId": scheduledId})
    assert r.status == "ok"
    assert r.data["fileName"] == f"meeting-{scheduledId}.ics"
    text = r.data["content"].decode("utf-8")
    assert "BEGIN:VCALENDAR\r\n" in text
    assert "VERSION:2.0\r\n" in text
    assert text.count("BEGIN:VEVENT") == 1
    assert "SUMMARY:IT 426 weekly\r\n" in text
    assert "DTSTART:20261102T150000Z\r\n" in text
    assert "DTEND:20261102T160000Z\r\n" in text
    assert "RRULE:FREQ=WEEKLY\r\n" in text


def test_export_cancelled_meeting_is_not_found():
    app, token, _, cancelledId = setup()
    r = app.meetingController.handleExportIcs({"token": token, "meetingId": cancelledId})
    assert r.status == "notFound"


def test_exported_bytes_import_back_with_same_times():
    app, token, scheduledId, _ = setup()
    content = app.meetingController.handleExportIcs({"token": token, "meetingId": scheduledId}).data["content"]
    slots = IcsParser().parseToSlots(content)
    assert len(slots) == 1
    assert slots[0].startTime == START
    assert slots[0].endTime == END


def test_no_token_is_unauthenticated():
    app, token, scheduledId, _ = setup()
    assert app.meetingController.handleExportIcs({"meetingId": scheduledId}).status == "unauthenticated"