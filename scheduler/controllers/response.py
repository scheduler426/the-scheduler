"""The result every controller handler returns, and the error-to-status mapping.

Handlers are written as return respond(lambda: ...). respond turns a normal
return into an ok Response and a known error raised below the controller
into the matching status, with the error text as the message. Any other
error is not caught.
"""

from __future__ import annotations

from typing import Any, Callable

from scheduler.infrastructure.email_service import MailDeliveryError
from scheduler.services.authentication_service import AuthenticationError


class Response:
    """A status, the returned data, and a message for errors."""
    OK = "ok"
    INVALID = "invalid"
    NOT_FOUND = "notFound"
    FORBIDDEN = "forbidden"
    UNAUTHENTICATED = "unauthenticated"
    MAIL_FAILED = "mailFailed"

    def __init__(self, status: str, data: Any = None, message: str = ""):
        self.status = status
        self.data = data
        self.message = message


def respond(action: Callable[[], Any]) -> Response:
    """Run action and wrap its result or its error in a Response."""
    try:
        return Response(Response.OK, data=action())
    except AuthenticationError as error:
        return Response(Response.UNAUTHENTICATED, message=str(error))
    except PermissionError as error:
        return Response(Response.FORBIDDEN, message=str(error))
    except LookupError as error:
        return Response(Response.NOT_FOUND, message=str(error))
    except ValueError as error:
        return Response(Response.INVALID, message=str(error))
    except MailDeliveryError as error:
        return Response(Response.MAIL_FAILED, message=str(error))
