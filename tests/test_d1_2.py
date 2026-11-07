"""D1-2: EmailService and the mailFailed status."""

from __future__ import annotations

import smtplib

import pytest

from scheduler.application import buildApplication
from scheduler.controllers.response import respond
from scheduler.infrastructure.duckdb_connection import DuckDBConnection
from scheduler.infrastructure.email_service import EmailService, MailDeliveryError

SMTP_VARIABLES = ("HOST", "PORT", "FROM", "USERNAME", "PASSWORD")


@pytest.fixture(autouse=True)
def clearSmtpEnvironment(monkeypatch):
    for name in SMTP_VARIABLES:
        monkeypatch.delenv(f"SCHEDULER_SMTP_{name}", raising=False)


def test_consoleModePrints(capsys):
    EmailService(host="console", sender="noreply@ilstu.edu").sendEmail("a@ilstu.edu", "Hi", "Body")
    output = capsys.readouterr().out
    assert "a@ilstu.edu" in output and "Hi" in output and "Body" in output


def test_consoleModeNeedsNoSender(capsys):
    EmailService(host="console").sendEmail("a@ilstu.edu", "Hi", "Body")
    assert "Body" in capsys.readouterr().out


def test_emptyHostRaises():
    with pytest.raises(MailDeliveryError):
        EmailService(host="", sender="x").sendEmail("a@ilstu.edu", "Hi", "Body")


def test_realHostWithoutSenderRaises():
    with pytest.raises(MailDeliveryError, match="SCHEDULER_SMTP_FROM"):
        EmailService(host="smtp.example.com").sendEmail("a@ilstu.edu", "Hi", "Body")


def test_constructorNeverRaises(monkeypatch):
    monkeypatch.setenv("SCHEDULER_SMTP_PORT", "not-a-number")
    EmailService()


def test_settingsComeFromEnvironment(monkeypatch, capsys):
    monkeypatch.setenv("SCHEDULER_SMTP_HOST", "console")
    EmailService().sendEmail("a@ilstu.edu", "Hi", "Body")
    assert "Body" in capsys.readouterr().out


def test_smtpErrorBecomesMailDeliveryError(monkeypatch):
    def refuse(*args, **kwargs):
        raise smtplib.SMTPConnectError(421, "unavailable")
    monkeypatch.setattr(smtplib, "SMTP", refuse)
    with pytest.raises(MailDeliveryError):
        EmailService(host="smtp.example.com", sender="x@ilstu.edu").sendEmail("a@ilstu.edu", "Hi", "Body")


def test_smtpLoginWhenUsernameSet(monkeypatch):
    calls = []

    class FakeSmtp:
        def __init__(self, host, port, timeout):
            calls.append(("connect", host, port))

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def starttls(self):
            calls.append(("starttls",))

        def login(self, username, password):
            calls.append(("login", username, password))

        def send_message(self, message):
            calls.append(("send", message["To"], message["From"]))

    monkeypatch.setattr(smtplib, "SMTP", FakeSmtp)
    EmailService(host="smtp.example.com", sender="x@ilstu.edu", username="u", password="p").sendEmail(
        "a@ilstu.edu", "Hi", "Body"
    )
    assert calls == [
        ("connect", "smtp.example.com", 587),
        ("starttls",),
        ("login", "u", "p"),
        ("send", "a@ilstu.edu", "x@ilstu.edu"),
    ]


def test_bulkEmailNamesFailedAddress(monkeypatch):
    service = EmailService(host="console")
    sent = []

    def fakeSend(to, subject, body):
        if to == "bad@ilstu.edu":
            raise MailDeliveryError("down")
        sent.append(to)

    monkeypatch.setattr(service, "sendEmail", fakeSend)
    with pytest.raises(MailDeliveryError, match="bad@ilstu.edu"):
        service.sendBulkEmail(["a@ilstu.edu", "bad@ilstu.edu", "c@ilstu.edu"], "Hi", "Body")
    assert sent == ["a@ilstu.edu"]


def test_bulkEmailSendsToEach(capsys):
    EmailService(host="console").sendBulkEmail(["a@ilstu.edu", "b@ilstu.edu"], "Hi", "Body")
    output = capsys.readouterr().out
    assert "a@ilstu.edu" in output and "b@ilstu.edu" in output


def test_attachmentPrintsNameAndSize(capsys):
    EmailService(host="console").sendEmailWithAttachment("a@ilstu.edu", "Hi", "Body", "meeting.ics", b"12345")
    output = capsys.readouterr().out
    assert "meeting.ics" in output and "5 bytes" in output and "12345" not in output


def test_buildApplicationWithoutMailSettings():
    app = buildApplication(DuckDBConnection(":memory:"), "test-secret")
    assert isinstance(app.emailService, EmailService)


def test_respondMapsMailDeliveryError():
    def fails():
        raise MailDeliveryError("x")
    result = respond(fails)
    assert result.status == "mailFailed" and result.message == "x"
