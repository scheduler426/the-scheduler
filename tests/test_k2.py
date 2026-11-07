"""K2: Response, respond, requireSession, close, and buildApplication."""

from __future__ import annotations

import pytest

from scheduler.application import buildApplication
from scheduler.controllers.response import Response, respond
from scheduler.domain.user import User
from scheduler.infrastructure.duckdb_connection import DuckDBConnection
from scheduler.infrastructure.password_hasher import PasswordHasher
from scheduler.infrastructure.session_manager import SessionManager
from scheduler.infrastructure.token_provider import TokenProvider
from scheduler.repositories.user_repository import UserRepository
from scheduler.services.authentication_service import AuthenticationError, AuthenticationService


def raises(error):
    def action():
        raise error
    return action


def test_buildApplication():
    app = buildApplication(DuckDBConnection(":memory:"), "test-secret")
    assert app.sessionManager is not None
    assert app.mailHost is None
    app.close()


def test_buildApplicationRequiresSecret():
    with pytest.raises(ValueError, match="secretKey is required"):
        buildApplication(DuckDBConnection(":memory:"), "")


def test_respondOk():
    result = respond(lambda: {"a": 1})
    assert result.status == Response.OK and result.data == {"a": 1}


@pytest.mark.parametrize(
    "error, status",
    [
        (AuthenticationError("x"), "unauthenticated"),
        (PermissionError("x"), "forbidden"),
        (LookupError("x"), "notFound"),
        (KeyError("x"), "notFound"),
        (ValueError("x"), "invalid"),
    ],
)
def test_respondMapsErrors(error, status):
    result = respond(raises(error))
    assert result.status == status
    assert result.data is None


def test_respondMessage():
    result = respond(raises(LookupError("x")))
    assert result.status == "notFound" and result.message == "x"


def test_respondLetsOtherErrorsThrough():
    with pytest.raises(RuntimeError):
        respond(raises(RuntimeError("boom")))


def test_authenticationErrorIsNotPermissionError():
    assert not issubclass(AuthenticationError, PermissionError)


def makeAuthService():
    hasher = PasswordHasher()
    userRepo = UserRepository(DuckDBConnection(":memory:"))
    userRepo.save(User(None, "ada@ilstu.edu", hasher.hash("secret12"), "Ada", "Lovelace"))
    return AuthenticationService(userRepo, SessionManager(TokenProvider("secret")), hasher)


def test_requireSession():
    authService = makeAuthService()
    with pytest.raises(AuthenticationError, match="Authentication required"):
        authService.requireSession(None)
    with pytest.raises(AuthenticationError, match="Authentication required"):
        authService.requireSession("")
    with pytest.raises(AuthenticationError, match="Session is not active"):
        authService.requireSession("bogus")
    session = authService.login("ada@ilstu.edu", "secret12")
    assert authService.requireSession(session.token).userId == session.userId


def test_closeClosesConnection():
    db = DuckDBConnection(":memory:")
    db.close()
    with pytest.raises(Exception):
        db.sql("SELECT 1")
