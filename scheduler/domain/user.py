"""A registered person. Profile fields live on this account, not on a separate profile type.

User keeps the name, email, password hash, reminder flag, and an in-memory
AvailabilitySchedule. UserRepository loads and saves the account, and
UserService registers and updates it. Hashing, sessions, and schedule
storage happen elsewhere. allowEmailReminders is only stored here.
"""

from __future__ import annotations

from typing import Optional

from scheduler.domain.availability_schedule import AvailabilitySchedule


class User:
    """Profile and credentials for one account.

    The schedule is created empty when the caller does not pass one.
    This class does not read DuckDB or check that the email is unique.
    """
    def __init__(
        self,
        userId: Optional[int],
        email: str,
        passwordHash: str,
        firstName: str,
        lastName: str,
        allowEmailReminders: bool = True,
        availabilitySchedule: Optional[AvailabilitySchedule] = None,
    ):
        self._userId = userId
        self._email = email
        self._passwordHash = passwordHash
        self._firstName = firstName
        self._lastName = lastName
        self._allowEmailReminders = allowEmailReminders
        self._availabilitySchedule = availabilitySchedule or AvailabilitySchedule(userId)

    @property
    def userId(self) -> Optional[int]:
        return self._userId

    @property
    def email(self) -> str:
        return self._email

    @property
    def passwordHash(self) -> str:
        return self._passwordHash

    @property
    def firstName(self) -> str:
        return self._firstName

    @property
    def lastName(self) -> str:
        return self._lastName

    @property
    def allowEmailReminders(self) -> bool:
        return self._allowEmailReminders

    @property
    def availabilitySchedule(self) -> AvailabilitySchedule:
        return self._availabilitySchedule
