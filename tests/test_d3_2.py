# Tests for D3-2: view and edit my availability

from datetime import datetime

from scheduler.application import buildApplication
from scheduler.infrastructure.duckdb_connection import DuckDBConnection

WEEKLY = {"startTime": datetime(2026, 11, 2, 15, 0), "endTime": datetime(2026, 11, 2, 16, 0), "cadence": "weekly"}
ICS = (b"BEGIN:VCALENDAR\r\nBEGIN:VEVENT\r\n"
       b"DTSTART:20261103T150000Z\r\nDTEND:20261103T160000Z\r\n"
       b"END:VEVENT\r\nEND:VCALENDAR\r\n")


def makeApp():
    app = buildApplication(DuckDBConnection(":memory:"), secretKey="test-secret", mailHost="console")
    app.userController.handleRegisterUser(
        {"email": "ada@ilstu.edu", "password": "secret12", "firstName": "Ada", "lastName": "Lovelace"}
    )
    token = app.authController.handleLogin({"email": "ada@ilstu.edu", "password": "secret12"}).data["token"]
    return app.availabilityController, token


def test_update_then_get():
    ctrl, token = makeApp()
    assert ctrl.handleUpdateSchedule({"token": token, "slots": [WEEKLY]}).status == "ok"
    slots = ctrl.handleGetSchedule({"token": token}).data["slots"]
    assert len(slots) == 1
    assert slots[0]["cadence"] == "weekly"


def test_empty_list_clears():
    ctrl, token = makeApp()
    ctrl.handleUpdateSchedule({"token": token, "slots": [WEEKLY]})
    assert ctrl.handleUpdateSchedule({"token": token, "slots": []}).status == "ok"
    assert ctrl.handleGetSchedule({"token": token}).data == {"slots": []}


def test_upload_valid_ics():
    ctrl, token = makeApp()
    assert ctrl.handleUploadIcs({"token": token, "fileName": "cal.ics", "fileBytes": ICS}).status == "ok"
    slots = ctrl.handleGetSchedule({"token": token}).data["slots"]
    assert [s["cadence"] for s in slots] == ["once"]


def test_upload_text_is_invalid_and_keeps_old_slots():
    ctrl, token = makeApp()
    ctrl.handleUploadIcs({"token": token, "fileName": "cal.ics", "fileBytes": ICS})
    assert ctrl.handleUploadIcs({"token": token, "fileName": "a.txt", "fileBytes": b"hello"}).status == "invalid"
    assert len(ctrl.handleGetSchedule({"token": token}).data["slots"]) == 1


def test_no_token_is_unauthenticated():
    ctrl, token = makeApp()
    assert ctrl.handleGetSchedule({}).status == "unauthenticated"
    assert ctrl.handleUpdateSchedule({"slots": []}).status == "unauthenticated"
    assert ctrl.handleUploadIcs({"fileName": "cal.ics", "fileBytes": ICS}).status == "unauthenticated"