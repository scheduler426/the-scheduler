"""Sends every email the app produces, or prints it in console mode.

Services pass in the recipient, subject, and body; the text itself comes
from the template factories. Settings left as None are read from the
SCHEDULER_SMTP_* environment variables. With host "console" the email is
printed instead of sent, and no sender address is needed. Any failure to
send becomes MailDeliveryError.
"""

from __future__ import annotations

import mimetypes
import os
import smtplib
from email.message import EmailMessage
from typing import Iterable, Optional


class MailDeliveryError(Exception):
    """Raised when an email cannot be sent."""


class EmailService:
    """SMTP sender with a console mode for tests and local development.

    The constructor never raises. Missing settings are reported when an
    email is sent. With a username, the connection uses STARTTLS and logs in.
    """
    CONSOLE = "console"
    DEFAULT_PORT = 587

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        sender: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self._host = host if host is not None else os.environ.get("SCHEDULER_SMTP_HOST")
        self._port = port if port is not None else self._portFromEnvironment()
        self._senderAddress = sender if sender is not None else os.environ.get("SCHEDULER_SMTP_FROM")
        self._username = username if username is not None else os.environ.get("SCHEDULER_SMTP_USERNAME")
        self._password = password if password is not None else os.environ.get("SCHEDULER_SMTP_PASSWORD")

    def sendEmail(self, to: str, subject: str, body: str) -> None:
        """Send one plain-text email, or print it in console mode."""
        self._deliver(self._buildMessage(to, subject, body))

    def sendBulkEmail(self, toList: Iterable[str], subject: str, body: str) -> None:
        """Send the same email to each address. Emails sent before a failure stay sent."""
        for to in toList:
            try:
                self.sendEmail(to, subject, body)
            except MailDeliveryError as error:
                raise MailDeliveryError(f"Email to {to} was not sent: {error}") from error

    def sendEmailWithAttachment(self, to: str, subject: str, body: str, filename: str, content: bytes) -> None:
        """Send one email with content attached as filename. Console mode prints the size, not the bytes."""
        message = self._buildMessage(to, subject, body)
        mimeType, _ = mimetypes.guess_type(filename)
        maintype, subtype = (mimeType or "application/octet-stream").split("/", 1)
        message.add_attachment(content, maintype=maintype, subtype=subtype, filename=filename)
        self._deliver(message, attachment=f"{filename} ({len(content)} bytes)")

    def _buildMessage(self, to: str, subject: str, body: str) -> EmailMessage:
        message = EmailMessage()
        message["To"] = to
        message["Subject"] = subject
        if self._senderAddress:
            message["From"] = self._senderAddress
        message.set_content(body)
        return message

    def _deliver(self, message: EmailMessage, attachment: Optional[str] = None) -> None:
        if not self._host:
            raise MailDeliveryError("SMTP host is not set (SCHEDULER_SMTP_HOST)")
        if self._host == self.CONSOLE:
            self._print(message, attachment)
            return
        if not self._senderAddress:
            raise MailDeliveryError("Sender address is not set (SCHEDULER_SMTP_FROM)")
        try:
            with smtplib.SMTP(self._host, self._port, timeout=30) as smtp:
                if self._username:
                    smtp.starttls()
                    smtp.login(self._username, self._password or "")
                smtp.send_message(message)
        except (smtplib.SMTPException, OSError) as error:
            raise MailDeliveryError(f"Email to {message['To']} was not sent: {error}") from error

    @staticmethod
    def _print(message: EmailMessage, attachment: Optional[str]) -> None:
        print(f"To: {message['To']}")
        print(f"Subject: {message['Subject']}")
        if attachment:
            print(f"Attachment: {attachment}")
        print()
        print(message.get_body().get_content())

    @classmethod
    def _portFromEnvironment(cls) -> int:
        try:
            return int(os.environ.get("SCHEDULER_SMTP_PORT") or cls.DEFAULT_PORT)
        except ValueError:
            return cls.DEFAULT_PORT
