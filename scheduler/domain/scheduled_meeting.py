from __future__ import annotations

from typing import Iterable, Optional

from scheduler.domain.time_slot import TimeSlot


class ScheduledMeeting:
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"

    def __init__(
        self,
        meetingId: Optional[int],
        groupId: int,
        meetingName: str,
        scheduledSlots: Optional[Iterable[TimeSlot]] = None,
        status: str = SCHEDULED,
    ):
        self._meetingId = meetingId
        self._groupId = groupId
        self._meetingName = meetingName
        self._scheduledSlots: list[TimeSlot] = list(scheduledSlots or [])
        self._status = status

    @property
    def meetingId(self) -> Optional[int]:
        return self._meetingId

    @property
    def groupId(self) -> int:
        return self._groupId

    @property
    def meetingName(self) -> str:
        return self._meetingName

    @property
    def scheduledSlots(self) -> list[TimeSlot]:
        return list(self._scheduledSlots)

    @property
    def status(self) -> str:
        return self._status

    def cancelMeeting(self) -> None:
        if self._status == self.CANCELLED:
            raise ValueError("Meeting is already cancelled")
        self._status = self.CANCELLED
