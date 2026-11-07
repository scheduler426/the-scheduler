"""D1-6: login and logout through AuthController."""

from __future__ import annotations

import pytest

from scheduler.application import buildApplication
from scheduler.infrastructure.duckdb_connection import DuckDBConnection

ADA = {"email": "ada@ilstu.edu", "password": "secret12", "firstName": "Ada", "lastName": "Lovelace"}


@pytest.fixture
def app():
    app = buildApplication(DuckDBConnection(":memory:"), "test-secret", mailHost="console")
    app.userController.handleRegisterUser(ADA)
    return app


def test_loginReturnsSession(app):
    response = app.authController.handleLogin({"email": "ada@ilstu.edu", "password": "secret12"})
    assert response.status == "ok"
    assert set(response.data) == {"userSessionId", "userId", "token", "loginTime", "expiryTime"}
    assert response.data["token"]


@pytest.mark.parametrize("email, password", [("ada@ilstu.edu", "wrong123"), ("nobody@ilstu.edu", "secret12")])
def test_loginFailureDoesNotSayWhich(app, email, password):
    response = app.authController.handleLogin({"email": email, "password": password})
    assert response.status == "forbidden"
    assert response.message == "Invalid email or password"


def test_logout(app):
    token = app.authController.handleLogin({"email": "ada@ilstu.edu", "password": "secret12"}).data["token"]
    assert app.authController.handleLogout({"token": token}).status == "ok"
    again = app.authController.handleLogout({"token": token})
    assert again.status == "unauthenticated"
    assert again.message == "Session is not active"


def test_logoutWithoutToken(app):
    response = app.authController.handleLogout({})
    assert response.status == "unauthenticated" and response.message == "Authentication required"
