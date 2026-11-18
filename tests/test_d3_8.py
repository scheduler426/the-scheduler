# Tests for D3-8: list my meetings

from datetime import datetime

import pytest

from scheduler.application import buildApplication
from scheduler.domain.scheduled_meeting import ScheduledMeeting
from scheduler.domain.time_slot import TimeSlot
from scheduler.infrastructure.duckdb_connection import DuckDBConnection
from scheduler.repositories.group_repository import GroupRepository
from scheduler.repositories.scheduled_meeting_repository import ScheduledMeetingRepository
from scheduler.services.group_service import GroupService
from scheduler.services.meeting_retrieval_service import MeetingRetrievalService


def makeApp():
    return buildApplication(DuckDBConnection(":memory:"), secretKey="test-secret", mailHost="console")


def makeUser(app, number):
    email = f"user{number}@ilstu.edu"
    app.userController.handleRegisterUser(
        {"email": email, "password": "secret12", "firstName": "User", "lastName": str(number)}
    )
    token = app.authController.handleLogin({"email": email, "password": "secret12"}).data["token"]
    userId = app.sessionManager.getSession(token).userId
    return token, userId


def setup():
    # One member with a scheduled meeting and a cancelled meeting, plus an outsider
    app = makeApp()
    token1, id1 = makeUser(app, 1)
    outsiderToken, outsiderId = makeUser(app, 2)
    groupRepo = GroupRepository(app.database)
    group = GroupService(groupRepo).createGroup(id1, "IT 426", "")

    slot = TimeSlot(datetime(2026, 11, 2, 15, 0), datetime(2026, 11, 2, 16, 0), "weekly")
    meetingRepo = ScheduledMeetingRepository(app.database)
    scheduledId = meetingRepo.save(ScheduledMeeting(None, group.groupId, "Scheduled one", [slot]))
    cancelled = ScheduledMeeting(None, group.groupId, "Cancelled one", [slot])
    cancelled.cancelMeeting()
    cancelledId = meetingRepo.save(cancelled)
    return app, meetingRepo, token1, id1, outsiderToken, outsiderId, scheduledId, cancelledId


def test_only_scheduled_meetings_are_listed():
    app, meetingRepo, token1, id1, _, _, scheduledId, cancelledId = setup()
    r = app.meetingController.handleGetMyMeetings({"token": token1})
    assert r.status == "ok"
    assert [m["meetingId"] for m in r.data] == [scheduledId]
    assert r.data[0]["meetingName"] == "Scheduled one"
    assert r.data[0]["status"] == "scheduled"
    assert r.data[0]["scheduledSlots"][0]["cadence"] == "weekly"


def test_cancelled_meeting_is_not_found():
    app, meetingRepo, token1, id1, _, _, scheduledId, cancelledId = setup()
    service = MeetingRetrievalService(meetingRepo, None, None)
    with pytest.raises(LookupError, match="Meeting not found"):
        service.getMeetingForUser(id1, cancelledId)


def test_scheduled_meeting_is_found():
    app, meetingRepo, token1, id1, _, _, scheduledId, cancelledId = setup()
    service = MeetingRetrievalService(meetingRepo, None, None)
    assert service.getMeetingForUser(id1, scheduledId).meetingName == "Scheduled one"


def test_non_member_gets_empty_list():
    app, meetingRepo, token1, id1, outsiderToken, outsiderId, scheduledId, cancelledId = setup()
    r = app.meetingController.handleGetMyMeetings({"token": outsiderToken})
    assert r.status == "ok"
    assert r.data == []
    service = MeetingRetrievalService(meetingRepo, None, None)
    with pytest.raises(LookupError):
        service.getMeetingForUser(outsiderId, scheduledId)


def test_no_token_is_unauthenticated():
    app = makeApp()
    assert app.meetingController.handleGetMyMeetings({}).status == "unauthenticated"