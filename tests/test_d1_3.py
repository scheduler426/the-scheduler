"""D1-3: AuthEmailTemplateFactory."""

from __future__ import annotations

from scheduler.infrastructure.auth_email_template_factory import AuthEmailTemplateFactory


def test_confirmationEmail():
    factory = AuthEmailTemplateFactory()
    text = factory.buildConfirmationEmail("Ada", "ada@ilstu.edu")
    assert "Ada" in text and "ada@ilstu.edu" in text
    assert not text.lower().startswith("subject")


def test_resetEmail():
    text = AuthEmailTemplateFactory().buildResetEmail("abc")
    assert "abc" in text and "reset your scheduler password" in text


def test_signInCodeEmail():
    text = AuthEmailTemplateFactory().buildEmailAuthenticationEmail("abc")
    assert "abc" in text and "sign-in code" in text


def test_templateCacheStartsEmpty():
    assert AuthEmailTemplateFactory().templateCache == {}
