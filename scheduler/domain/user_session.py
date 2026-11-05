"""One logged-in session for a user.

SessionManager creates and tracks these in memory. AuthenticationService
returns one from login. The token is signed by TokenProvider.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class UserSession:
    userSessionId: str
    userId: int
    token: str
    loginTime: datetime
    expiryTime: datetime
