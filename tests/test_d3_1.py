# Tests for D3-1: import an .ics calendar

import pytest

from scheduler.application import buildApplication
from scheduler.infrastructure.duckdb_connection import DuckDBConnection
from scheduler.infrastructure.ics_parser import IcsParser
from scheduler.repositories.availability_schedule_repository import AvailabilityScheduleRepository
from scheduler.services.availability_service import AvailabilityService

ICS = (b"BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\n"
       b"DTSTART:20261103T150000Z\r\nDTEND:20261103T160000Z\r\n"
       b"END:VEVENT\r\nEND:VCALENDAR\r\n")


def makeService():
    db = DuckDBConnection(":memory:")
    app = buildApplication(db, secretKey="test-secret", mailHost="console")
    app.userController.handleRegisterUser(
        {"email": "ada@ilstu.edu", "password": "secret12", "firstName": "Ada", "lastName": "Lovelace"}
    )
    token = app.authController.handleLogin({"email": "ada@ilstu.edu", "password": "secret12"}).data["token"]
    userId = app.sessionManager.getSession(token).userId
    return AvailabilityService(AvailabilityScheduleRepository(db), IcsParser()), userId


def test_parse_one_event():
    slots = IcsParser().parseToSlots(ICS)
    assert len(slots) == 1
    assert slots[0].startTime.hour == 15
    assert slots[0].endTime.hour == 16
    assert slots[0].cadence == "once"


def test_bad_file_keeps_old_slots():
    service, userId = makeService()
    service.importIcsCalendar(userId, "cal.ics", ICS)
    with pytest.raises(ValueError):
        service.importIcsCalendar(userId, "cal.ics", b"hello")
    slots = service.getUserAvailability(userId).retrieveAvailabilitySchedule()
    assert len(slots) == 1