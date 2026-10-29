from __future__ import annotations

from typing import Optional

from scheduler.domain.availability_schedule import AvailabilitySchedule


class User:
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
