"""D1-7: forgot password and reset password through PasswordRecoveryController."""

from __future__ import annotations

import re

import pytest

from scheduler.application import buildApplication
from scheduler.infrastructure.duckdb_connection import DuckDBConnection

ADA = {"email": "ada@ilstu.edu", "password": "secret12", "firstName": "Ada", "lastName": "Lovelace"}
SENT = "If an account exists for that email, a reset link has been sent."


@pytest.fixture
def app(capsys):
    app = buildApplication(DuckDBConnection(":memory:"), "test-secret", mailHost="console")
    app.userController.handleRegisterUser(ADA)
    capsys.readouterr()
    return app


def summary(response):
    return response.status, response.data, response.message


def test_forgotPasswordSameResponseForAnyEmail(app):
    unknown = app.passwordRecoveryController.handleForgotPassword({"email": "nobody@ilstu.edu"})
    known = app.passwordRecoveryController.handleForgotPassword({"email": "ada@ilstu.edu"})
    assert summary(unknown) == summary(known) == ("ok", None, SENT)


def test_forgotPasswordNeedsEmail(app):
    response = app.passwordRecoveryController.handleForgotPassword({})
    assert response.status == "invalid" and response.message == "Email is required"


def test_resetWithPrintedToken(app, capsys):
    app.passwordRecoveryController.handleForgotPassword({"email": "ada@ilstu.edu"})
    token = re.search(r"reset your scheduler password: (\S+)", capsys.readouterr().out).group(1)
    response = app.passwordRecoveryController.handleResetPassword({"token": token, "newPassword": "newpass1"})
    assert response.status == "ok" and response.data is None
    oldLogin = app.authController.handleLogin({"email": "ada@ilstu.edu", "password": "secret12"})
    newLogin = app.authController.handleLogin({"email": "ada@ilstu.edu", "password": "newpass1"})
    assert oldLogin.status == "forbidden"
    assert newLogin.status == "ok"


def test_resetWithLoginTokenIsInvalid(app):
    loginToken = app.authController.handleLogin({"email": "ada@ilstu.edu", "password": "secret12"}).data["token"]
    response = app.passwordRecoveryController.handleResetPassword({"token": loginToken, "newPassword": "newpass1"})
    assert response.status == "invalid" and response.message == "Invalid or expired token"


def test_resetWithWeakPasswordIsInvalid(app, capsys):
    app.passwordRecoveryController.handleForgotPassword({"email": "ada@ilstu.edu"})
    token = re.search(r"reset your scheduler password: (\S+)", capsys.readouterr().out).group(1)
    response = app.passwordRecoveryController.handleResetPassword({"token": token, "newPassword": "short"})
    assert response.status == "invalid"


def test_resetForDeletedUserIsNotFound(app, capsys):
    app.passwordRecoveryController.handleForgotPassword({"email": "ada@ilstu.edu"})
    token = re.search(r"reset your scheduler password: (\S+)", capsys.readouterr().out).group(1)
    loginToken = app.authController.handleLogin({"email": "ada@ilstu.edu", "password": "secret12"}).data["token"]
    app.userController.handleDeleteAccount({"token": loginToken, "password": "secret12"})
    response = app.passwordRecoveryController.handleResetPassword({"token": token, "newPassword": "newpass1"})
    assert response.status == "notFound"
