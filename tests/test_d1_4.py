"""D1-4: PasswordRecoveryService."""

from __future__ import annotations

import re

import pytest

from scheduler.application import buildApplication
from scheduler.domain.user import User
from scheduler.infrastructure.auth_email_template_factory import AuthEmailTemplateFactory
from scheduler.infrastructure.duckdb_connection import DuckDBConnection
from scheduler.infrastructure.email_service import EmailService, MailDeliveryError
from scheduler.infrastructure.password_hasher import PasswordHasher
from scheduler.infrastructure.session_manager import SessionManager
from scheduler.infrastructure.token_provider import TokenProvider
from scheduler.repositories.user_repository import UserRepository
from scheduler.services.password_recovery_service import PasswordRecoveryService

SECRET = "test-secret"


@pytest.fixture
def setup():
    hasher = PasswordHasher()
    userRepo = UserRepository(DuckDBConnection(":memory:"))
    userId = userRepo.save(User(None, "ada@ilstu.edu", hasher.hash("secret12"), "Ada", "Lovelace"))
    tokenProvider = TokenProvider(SECRET, tokenValidityInMs=3_600_000)
    service = PasswordRecoveryService(
        userRepo, tokenProvider, EmailService(host="console"), AuthEmailTemplateFactory(), hasher
    )
    return service, userRepo, tokenProvider, hasher, userId


def printedToken(output: str) -> str:
    return re.search(r"reset your scheduler password: (\S+)", output).group(1)


def test_buildApplicationCreatesRecoveryService():
    buildApplication(DuckDBConnection(":memory:"), SECRET, mailHost="console")


def test_requestResetPrintsTokenForUser(setup, capsys):
    service, _, tokenProvider, _, userId = setup
    service.requestResetLink(" Ada@ILSTU.edu ")
    output = capsys.readouterr().out
    assert output.count("To: ada@ilstu.edu") == 1
    assert "Reset your scheduler password" in output
    assert tokenProvider.getPayload(printedToken(output)) == f"reset:{userId}"


def test_completeResetChangesPassword(setup, capsys):
    service, userRepo, _, hasher, userId = setup
    service.requestResetLink("ada@ilstu.edu")
    service.completePasswordReset(printedToken(capsys.readouterr().out), "newpass1")
    user = userRepo.findById(userId)
    assert hasher.verify("newpass1", user.passwordHash)
    assert not hasher.verify("secret12", user.passwordHash)
    assert (user.email, user.firstName, user.lastName) == ("ada@ilstu.edu", "Ada", "Lovelace")


@pytest.mark.parametrize("email", ["nobody@ilstu.edu", "not-an-email", "", None])
def test_unknownOrBadEmailSendsNothing(setup, capsys, email):
    service = setup[0]
    service.requestResetLink(email)
    assert capsys.readouterr().out == ""


def test_sendFailureIsSwallowed(setup, monkeypatch):
    service = setup[0]

    def fail(*args):
        raise MailDeliveryError("down")

    monkeypatch.setattr(service._emailService, "sendEmail", fail)
    service.requestResetLink("ada@ilstu.edu")


def test_loginTokenIsRejected(setup):
    service = setup[0]
    loginToken = SessionManager(TokenProvider(SECRET)).createSession(1).token
    with pytest.raises(ValueError, match="Invalid or expired token"):
        service.completePasswordReset(loginToken, "newpass1")


def test_garbageTokenIsRejected(setup):
    with pytest.raises(ValueError, match="Invalid or expired token"):
        setup[0].completePasswordReset("garbage", "newpass1")


def test_weakPasswordIsRejected(setup):
    service, _, tokenProvider, _, userId = setup
    token = tokenProvider.generateToken(f"reset:{userId}")
    for weak in ["short1", "lettersonly", "12345678"]:
        with pytest.raises(ValueError, match="at least 8 characters"):
            service.completePasswordReset(token, weak)


def test_deletedUserIsNotFound(setup):
    service, userRepo, tokenProvider, _, userId = setup
    token = tokenProvider.generateToken(f"reset:{userId}")
    userRepo.delete(userId)
    with pytest.raises(LookupError, match="User not found"):
        service.completePasswordReset(token, "newpass1")
