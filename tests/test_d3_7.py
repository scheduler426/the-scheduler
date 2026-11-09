# Tests for D3-7: confirm the meeting time

from datetime import datetime, timedelta

from scheduler.application import buildApplication
from scheduler.domain.meeting_poll import MeetingPoll
from scheduler.domain.time_slot import TimeSlot
from scheduler.infrastructure.duckdb_connection import DuckDBConnection
from scheduler.repositories.group_repository import GroupRepository
from scheduler.repositories.meeting_poll_repository import MeetingPollRepository
from scheduler.services.group_service import GroupService


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
    # Two members and one outsider, plus a poll with two suggestions
    app = makeApp()
    token1, id1 = makeUser(app, 1)
    token2, id2 = makeUser(app, 2)
    outsiderToken, _ = makeUser(app, 3)
    groupRepo = GroupRepository(app.database)
    group = GroupService(groupRepo).createGroup(id1, "IT 426", "")
    groupRepo.addMember(group.groupId, id2)
    suggestions = {
        1: TimeSlot(datetime(2026, 11, 2, 15, 0), datetime(2026, 11, 2, 16, 0), "weekly"),
        2: TimeSlot(datetime(2026, 11, 3, 15, 0), datetime(2026, 11, 3, 16, 0), "weekly"),
    }
    poll = MeetingPoll(None, group.groupId, datetime.now() + timedelta(days=2), True, suggestions)
    pollId = MeetingPollRepository(app.database).save(poll)
    return app, group.groupId, pollId, token1, token2, outsiderToken


def vote(app, token, pollId, first, second):
    return app.voteController.handleCastVote(
        {
            "token": token,
            "pollId": pollId,
            "choices": [
                {"suggestionId": 1, "preference": first},
                {"suggestionId": 2, "preference": second},
            ],
        }
    )


def test_default_picks_top_voted_slot(capsys):
    app, groupId, pollId, token1, token2, _ = setup()
    # Tally: suggestion 1 = yes (1.0), suggestion 2 = maybe (0.5)
    vote(app, token1, pollId, "Yes", "If need be")
    r = app.schedulingController.handleFinalizeMeeting({"token": token1, "groupId": groupId})
    assert r.status == "ok"
    assert r.data["meetingName"] == "Group meeting"
    assert r.data["scheduledSlots"][0]["startTime"] == datetime(2026, 11, 2, 15, 0)
    # The poll is now inactive
    assert MeetingPollRepository(app.database).findActiveByGroupId(groupId) is None
    # A console email names the meeting and the time
    out = capsys.readouterr().out
    assert "Group meeting" in out
    assert "2026-11-02 15:00:00" in out


def test_explicit_suggestion_is_used():
    app, groupId, pollId, token1, token2, _ = setup()
    vote(app, token1, pollId, "Yes", "If need be")
    r = app.schedulingController.handleFinalizeMeeting(
        {"token": token1, "groupId": groupId, "suggestionId": 2, "meetingName": "IT 426 weekly"}
    )
    assert r.status == "ok"
    assert r.data["meetingName"] == "IT 426 weekly"
    assert r.data["scheduledSlots"][0]["startTime"] == datetime(2026, 11, 3, 15, 0)


def test_everyone_voted_no_is_invalid():
    app, groupId, pollId, token1, token2, _ = setup()
    vote(app, token1, pollId, "Can't make it", "Can't make it")
    vote(app, token2, pollId, "Can't make it", "Can't make it")
    r = app.schedulingController.handleFinalizeMeeting({"token": token1, "groupId": groupId})
    assert r.status == "invalid"
    assert r.message == "No suggestion has a yes or maybe vote"


def test_non_member_is_forbidden_and_poll_stays_active():
    app, groupId, pollId, token1, token2, outsiderToken = setup()
    vote(app, token1, pollId, "Yes", "If need be")
    r = app.schedulingController.handleFinalizeMeeting({"token": outsiderToken, "groupId": groupId})
    assert r.status == "forbidden"
    assert MeetingPollRepository(app.database).findActiveByGroupId(groupId) is not None


def test_no_active_poll_is_not_found():
    app, groupId, pollId, token1, token2, _ = setup()
    app.schedulingController.handleResetPoll({"token": token1, "groupId": groupId})
    r = app.schedulingController.handleFinalizeMeeting({"token": token1, "groupId": groupId})
    assert r.status == "notFound"


def test_no_token_is_unauthenticated():
    app, groupId, *_ = setup()
    assert app.schedulingController.handleFinalizeMeeting({"groupId": groupId}).status == "unauthenticated"