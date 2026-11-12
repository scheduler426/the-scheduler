# Tests for D3-4: vote and see poll status

from datetime import datetime, timedelta

from scheduler.application import buildApplication
from scheduler.domain.meeting_poll import MeetingPoll
from scheduler.domain.time_slot import TimeSlot
from scheduler.infrastructure.duckdb_connection import DuckDBConnection
from scheduler.repositories.group_repository import GroupRepository
from scheduler.repositories.meeting_poll_repository import MeetingPollRepository
from scheduler.repositories.vote_repository import VoteRepository
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


def makeGroup(app, creatorId, memberIds):
    groupRepo = GroupRepository(app.database)
    group = GroupService(groupRepo).createGroup(creatorId, "Project", "")
    for memberId in memberIds:
        groupRepo.addMember(group.groupId, memberId)
    return group.groupId


def makePoll(app, groupId):
    # A poll with two suggestions, closing in two days
    suggestions = {
        1: TimeSlot(datetime(2026, 11, 2, 15, 0), datetime(2026, 11, 2, 16, 0), "weekly"),
        2: TimeSlot(datetime(2026, 11, 3, 15, 0), datetime(2026, 11, 3, 16, 0), "weekly"),
    }
    poll = MeetingPoll(None, groupId, datetime.now() + timedelta(days=2), True, suggestions)
    return MeetingPollRepository(app.database).save(poll)


def setup():
    # Two members (user 1 votes, user 2 does not) and one outsider
    app = makeApp()
    token1, id1 = makeUser(app, 1)
    token2, id2 = makeUser(app, 2)
    outsiderToken, _ = makeUser(app, 3)
    groupId = makeGroup(app, id1, [id2])
    pollId = makePoll(app, groupId)
    return app, groupId, pollId, token1, id1, id2, outsiderToken


CHOICES = [
    {"suggestionId": 1, "preference": "Yes"},
    {"suggestionId": 2, "preference": "If need be"},
]


def test_vote_is_stored_as_yes_and_maybe():
    app, groupId, pollId, token1, id1, id2, _ = setup()
    r = app.voteController.handleCastVote({"token": token1, "pollId": pollId, "choices": CHOICES})
    assert r.status == "ok"
    stored = {v.suggestionId: v.votePreference for v in VoteRepository(app.database).findByPollAndUser(pollId, id1)}
    assert stored == {1: "yes", 2: "maybe"}


def test_poll_status_after_voting():
    app, groupId, pollId, token1, id1, id2, _ = setup()
    app.voteController.handleCastVote({"token": token1, "pollId": pollId, "choices": CHOICES})
    r = app.voteController.handleGetPollStatus({"token": token1, "groupId": groupId})
    assert r.status == "ok"
    voted = [getattr(u, "userId", u) for u in r.data["alreadyVoted"]]
    assert id1 in voted
    unvotedIds = [u["userId"] for u in r.data["unvotedMembers"]]
    assert id1 not in unvotedIds
    assert id2 in unvotedIds
    assert r.data["voteTally"] == {1: 1.0, 2: 0.5}


def test_changing_a_vote_updates_the_same_row():
    app, groupId, pollId, token1, id1, id2, _ = setup()
    app.voteController.handleCastVote({"token": token1, "pollId": pollId, "choices": CHOICES})
    r = app.voteController.handleCastVote(
        {"token": token1, "pollId": pollId, "choices": [{"suggestionId": 1, "preference": "Can't make it"}]}
    )
    assert r.status == "ok"
    votes = VoteRepository(app.database).findByPollAndUser(pollId, id1)
    assert len(votes) == 2
    stored = {v.suggestionId: v.votePreference for v in votes}
    assert stored == {1: "no", 2: "maybe"}


def test_bad_label_is_invalid():
    app, groupId, pollId, token1, *_ = setup()
    r = app.voteController.handleCastVote(
        {"token": token1, "pollId": pollId, "choices": [{"suggestionId": 1, "preference": "sure"}]}
    )
    assert r.status == "invalid"


def test_non_member_is_forbidden():
    app, groupId, pollId, token1, id1, id2, outsiderToken = setup()
    r = app.voteController.handleCastVote({"token": outsiderToken, "pollId": pollId, "choices": CHOICES})
    assert r.status == "forbidden"
    r = app.voteController.handleGetPollStatus({"token": outsiderToken, "groupId": groupId})
    assert r.status == "forbidden"


def test_group_with_no_poll_is_not_found():
    app = makeApp()
    token1, id1 = makeUser(app, 1)
    groupId = makeGroup(app, id1, [])
    r = app.voteController.handleGetPollStatus({"token": token1, "groupId": groupId})
    assert r.status == "notFound"


def test_no_token_is_unauthenticated():
    app, groupId, pollId, *_ = setup()
    assert app.voteController.handleCastVote({"pollId": pollId, "choices": CHOICES}).status == "unauthenticated"
    assert app.voteController.handleGetPollStatus({"groupId": groupId}).status == "unauthenticated"