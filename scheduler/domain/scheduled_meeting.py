"""A meeting a group has already placed on the calendar.

MeetingFinalizationService creates one from a chosen poll suggestion.
ScheduledMeetingRepository loads and saves the meeting and its slots.
cancelMeeting changes only the status held on this object.
"""

from __future__ import annotations

from typing import Iterable, Optional

from scheduler.domain.time_slot import TimeSlot


class ScheduledMeeting:
    """Name, status, and chosen TimeSlot values for one group meeting.

    Status starts as scheduled. Cancelling sets it to cancelled and refuses
    a second cancel. Members are not told, and nobody's availability changes.
    """
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
        """Mark the meeting cancelled."""
        if self._status == self.CANCELLED:
            raise ValueError("Meeting is already cancelled")
        self._status = self.CANCELLED
