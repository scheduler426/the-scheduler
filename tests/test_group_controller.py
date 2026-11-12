"""Authenticated group requests through GroupController."""

from __future__ import annotations

import pytest

from scheduler.application import buildApplication
from scheduler.infrastructure.duckdb_connection import DuckDBConnection


@pytest.fixture
def appAndToken():
    app = buildApplication(DuckDBConnection(":memory:"), "test-secret", mailHost="console")
    response = app.userController.handleRegisterUser(
        {"email": "group.member@ilstu.edu", "password": "secret12", "firstName": "Group", "lastName": "Member"}
    )
    assert response.status == "ok"
    userId = response.data["userId"]
    token = app.sessionManager.createSession(userId).token
    yield app, token
    app.close()


def test_groupControllerHandlesGroupLifecycle(appAndToken):
    app, token = appAndToken
    created = app.groupController.handleCreateGroup(
        {"token": token, "name": "Study group", "description": "Calculus"}
    )
    assert created.status == "ok"
    assert set(created.data) == {"groupId", "groupName", "description"}
    assert created.data["groupName"] == "Study group"

    groupId = created.data["groupId"]
    assert app.groupController.handleGetMyGroups({"token": token}).data == [created.data]

    modified = app.groupController.handleEditGroup(
        {"token": token, "groupId": groupId, "name": "Updated group"}
    )
    assert modified.status == "ok"
    assert app.groupController.handleGetMyGroups({"token": token}).data[0] == {
        "groupId": groupId,
        "groupName": "Updated group",
        "description": "Calculus",
    }

    deleted = app.groupController.handleDeleteGroup({"token": token, "groupId": groupId})
    assert deleted.status == "ok"
    assert app.groupController.handleGetMyGroups({"token": token}).data == []


def test_groupControllerRequiresSession(appAndToken):
    app, _ = appAndToken

    response = app.groupController.handleGetMyGroups({})

    assert response.status == "unauthenticated"


def test_groupControllerRequiresGroupName(appAndToken):
    app, token = appAndToken

    response = app.groupController.handleCreateGroup({"token": token})

    assert response.status == "invalid"
    assert response.message == "groupName is required"


def test_groupControllerRejectsBlankName(appAndToken):
    app, token = appAndToken

    response = app.groupController.handleCreateGroup({"token": token, "name": " "})

    assert response.status == "invalid"
    assert response.message == "groupName is required"
