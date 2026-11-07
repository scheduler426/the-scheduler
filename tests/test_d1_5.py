"""D1-5: sign-up, profile update, and account deletion through UserController."""

from __future__ import annotations

import pytest

from scheduler.application import buildApplication
from scheduler.infrastructure.duckdb_connection import DuckDBConnection
from scheduler.infrastructure.session_manager import SessionManager
from scheduler.infrastructure.token_provider import TokenProvider

ADA = {"email": "ada@ilstu.edu", "password": "secret12", "firstName": "Ada", "lastName": "Lovelace"}


@pytest.fixture
def app():
    return buildApplication(DuckDBConnection(":memory:"), "test-secret", mailHost="console")


def login(app, email="ada@ilstu.edu", password="secret12") -> str:
    return app.sessionManager.createSession(
        app.database.sql("SELECT userId FROM users WHERE email = ?", [email]).fetchone()[0]
    ).token


def test_registerReturnsPublicUser(app, capsys):
    response = app.userController.handleRegisterUser(ADA)
    assert response.status == "ok"
    assert set(response.data) == {"userId", "email", "firstName", "lastName", "allowEmailReminders"}
    assert response.data["email"] == "ada@ilstu.edu"
    output = capsys.readouterr().out
    assert "To: ada@ilstu.edu" in output and "Your scheduler account" in output and "Ada" in output


def test_registerRejectsNonIlstuEmail(app):
    response = app.userController.handleRegisterUser({**ADA, "email": "ada@gmail.com"})
    assert response.status == "invalid"
    assert response.message == "Email must end with @ilstu.edu"


@pytest.mark.parametrize("password", ["short", "lettersonly", "12345678"])
def test_registerRejectsWeakPassword(app, password):
    response = app.userController.handleRegisterUser({**ADA, "password": password})
    assert response.status == "invalid"
    assert "at least 8 characters" in response.message


def test_registerRejectsDuplicate(app):
    app.userController.handleRegisterUser(ADA)
    assert app.userController.handleRegisterUser(ADA).status == "invalid"


def test_registerKeepsAccountWhenMailFails():
    app = buildApplication(DuckDBConnection(":memory:"), "test-secret", mailHost="")
    response = app.userController.handleRegisterUser(ADA)
    assert response.status == "mailFailed"
    assert "was created but the confirmation email was not sent" in response.message
    assert app.database.sql("SELECT count(*) FROM users").fetchone()[0] == 1


def test_updateProfile(app):
    app.userController.handleRegisterUser(ADA)
    token = login(app)
    request = {"token": token, "email": "ada.l@ilstu.edu", "firstName": "Ada", "lastName": "King"}
    response = app.userController.handleUpdateProfile(request)
    assert response.status == "ok" and response.data is None
    row = app.database.sql("SELECT email, lastName FROM users").fetchone()
    assert row == ("ada.l@ilstu.edu", "King")


def test_updateProfileNeedsSession(app):
    app.userController.handleRegisterUser(ADA)
    request = {"email": "ada@ilstu.edu", "firstName": "Ada", "lastName": "King"}
    assert app.userController.handleUpdateProfile(request).status == "unauthenticated"


def test_deleteAccount(app):
    app.userController.handleRegisterUser(ADA)
    token = login(app)
    otherToken = login(app)
    wrong = app.userController.handleDeleteAccount({"token": token, "password": "wrong123"})
    assert wrong.status == "forbidden"
    right = app.userController.handleDeleteAccount({"token": token, "password": "secret12"})
    assert right.status == "ok"
    request = {"token": otherToken, "email": "ada@ilstu.edu", "firstName": "Ada", "lastName": "L"}
    assert app.userController.handleUpdateProfile(request).status == "unauthenticated"
    assert app.database.sql("SELECT count(*) FROM users").fetchone()[0] == 0


def test_removeSessionsForUser():
    manager = SessionManager(TokenProvider("secret"))
    first, second, other = manager.createSession(1), manager.createSession(1), manager.createSession(2)
    manager.removeSessionsForUser(1)
    assert manager.getSession(first.token) is None
    assert manager.getSession(second.token) is None
    assert manager.getSession(other.token).userId == 2
