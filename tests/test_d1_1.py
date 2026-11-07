"""D1-1: SessionManager returns UserSession copies and login returns a UserSession."""

from __future__ import annotations

from scheduler.domain.user import User
from scheduler.domain.user_session import UserSession
from scheduler.infrastructure.duckdb_connection import DuckDBConnection
from scheduler.infrastructure.password_hasher import PasswordHasher
from scheduler.infrastructure.session_manager import SessionManager
from scheduler.infrastructure.token_provider import TokenProvider
from scheduler.repositories.user_repository import UserRepository
from scheduler.services.authentication_service import AuthenticationService


def test_sessionManagerReturnsCopies():
    manager = SessionManager(TokenProvider("secret"))
    session = manager.createSession(5)
    assert session.userId == 5 and session.token
    assert manager.getSession(session.token).userId == 5
    assert manager.getSession("missing") is None
    copy = manager.getSession(session.token)
    copy.userId = 99
    assert manager.getSession(session.token).userId == 5


def test_extendAndRemoveSession():
    manager = SessionManager(TokenProvider("secret"))
    session = manager.createSession(5)
    manager.extendSession(session.token, 60)
    assert manager.getSession(session.token).expiryTime > session.expiryTime
    manager.removeSession(session.token)
    assert manager.getSession(session.token) is None


def test_loginReturnsUserSession():
    hasher = PasswordHasher()
    userRepo = UserRepository(DuckDBConnection(":memory:"))
    userId = userRepo.save(User(None, "ada@ilstu.edu", hasher.hash("secret12"), "Ada", "Lovelace"))
    authService = AuthenticationService(userRepo, SessionManager(TokenProvider("secret")), hasher)
    session = authService.login("ada@ilstu.edu", "secret12")
    assert isinstance(session, UserSession)
    assert session.userId == userId
