"""Writes the body text of account emails: sign-up confirmation, password reset, and sign-in code.

Callers choose the subject and send the text through EmailService. This
class does not send mail, open the database, or create tokens.
"""

from __future__ import annotations


class AuthEmailTemplateFactory:
    """Plain-text bodies for the account emails."""
    def __init__(self):
        self.templateCache: dict[str, str] = {}

    def buildConfirmationEmail(self, firstName: str, email: str) -> str:
        return (
            f"Welcome to the scheduler, {firstName}.\n"
            f"Your account {email} is ready.\n"
            "\n"
            "If you did not create this account, you can ignore this email.\n"
        )

    def buildResetEmail(self, token: str) -> str:
        return (
            f"Use this token to reset your scheduler password: {token}\n"
            "\n"
            "The token expires in one hour. If you did not ask to reset your password, "
            "you can ignore this email.\n"
        )

    def buildEmailAuthenticationEmail(self, token: str) -> str:
        return (
            f"Your scheduler sign-in code is: {token}\n"
            "\n"
            "If you did not try to sign in, you can ignore this email.\n"
        )
