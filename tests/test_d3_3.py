# Tests for D3-3: generate and reset meeting suggestions

import time
from datetime import datetime

from scheduler.application import buildApplication
from scheduler.infrastructure.duckdb_connection import DuckDBConnection
from scheduler.repositories.group_repository import GroupRepository
from scheduler.services.group_service import GroupService

WEEKLY = {"startTime": datetime(2026, 11, 2, 15, 0), "endTime": datetime(2026, 11, 2, 16, 0), "cadence": "weekly"}
WINDOW = {"windowStart": datetime(2026, 11, 2, 9, 0), "windowEnd": datetime(2026, 11, 2, 17, 0)}


def makeApp():
    return buildApplication(DuckDBConnection(":memory:"), secretKey="test-secret", mailHost="console")


def makeUser(app, number, slots=None):
    # Register and log in a user. Optionally give them availability.
    email = f"user{number}@ilstu.edu"
    app.userController.handleRegisterUser(
        {"email": email, "password": "secret12", "firstName": "User", "lastName": str(number)}
    )
    token = app.authController.handleLogin({"email": email, "password": "secret12"}).data["token"]
    userId = app.sessionManager.getSession(token).userId
    if slots is not None:
        app.availabilityController.handleUpdateSchedule({"token": token, "slots": slots})
    return token, userId


def makeGroup(app, creatorId, memberIds):
    # Create a group and add the other members to it
    groupRepo = GroupRepository(app.database)
    group = GroupService(groupRepo).createGroup(creatorId, "Project", "")
    for memberId in memberIds:
        groupRepo.addMember(group.groupId, memberId)
    return group.groupId


def makeGroupWithTwoMembers():
    app = makeApp()
    token1, id1 = makeUser(app, 1, [WEEKLY])
    token2, id2 = makeUser(app, 2, [WEEKLY])
    outsiderToken, _ = makeUser(app, 3)
    groupId = makeGroup(app, id1, [id2])
    return app, groupId, token1, outsiderToken


def test_outsider_cannot_generate():
    app, groupId, token1, outsiderToken = makeGroupWithTwoMembers()
    r = app.schedulingController.handleGenerateSuggestions(
        {"token": outsiderToken, "groupId": groupId, **WINDOW}
    )
    assert r.status == "forbidden"


def test_member_generates_weekly_suggestions():
    app, groupId, token1, _ = makeGroupWithTwoMembers()
    r = app.schedulingController.handleGenerateSuggestions({"token": token1, "groupId": groupId, **WINDOW})
    assert r.status == "ok"
    print(r.data["suggestions"])
    assert len(r.data["suggestions"]) >= 1
    assert all(s["cadence"] == "weekly" for s in r.data["suggestions"])


def test_bad_cadence_is_invalid():
    app, groupId, token1, _ = makeGroupWithTwoMembers()
    r = app.schedulingController.handleGenerateSuggestions(
        {"token": token1, "groupId": groupId, "cadence": "monthly", **WINDOW}
    )
    assert r.status == "invalid"


def test_no_shared_free_time_is_invalid():
    app, groupId, token1, _ = makeGroupWithTwoMembers()
    r = app.schedulingController.handleGenerateSuggestions(
        {
            "token": token1,
            "groupId": groupId,
            "windowStart": datetime(2026, 11, 2, 9, 0),
            "windowEnd": datetime(2026, 11, 2, 12, 0),
        }
    )
    assert r.status == "invalid"
    assert r.message == "No member availability matches the requested constraints"


def test_reset_twice_is_ok():
    app, groupId, token1, _ = makeGroupWithTwoMembers()
    app.schedulingController.handleGenerateSuggestions({"token": token1, "groupId": groupId, **WINDOW})
    assert app.schedulingController.handleResetPoll({"token": token1, "groupId": groupId}).status == "ok"
    assert app.schedulingController.handleResetPoll({"token": token1, "groupId": groupId}).status == "ok"


def test_outsider_cannot_reset():
    app, groupId, token1, outsiderToken = makeGroupWithTwoMembers()
    r = app.schedulingController.handleResetPoll({"token": outsiderToken, "groupId": groupId})
    assert r.status == "forbidden"


def test_nineteen_members_finish_under_two_seconds():
    app = makeApp()
    firstToken, firstId = makeUser(app, 1, [WEEKLY])
    others = [makeUser(app, n, [WEEKLY])[1] for n in range(2, 20)]
    groupId = makeGroup(app, firstId, others)
    start = time.perf_counter()
    r = app.schedulingController.handleGenerateSuggestions({"token": firstToken, "groupId": groupId, **WINDOW})
    elapsed = time.perf_counter() - start
    assert r.status == "ok"
    assert elapsed < 2